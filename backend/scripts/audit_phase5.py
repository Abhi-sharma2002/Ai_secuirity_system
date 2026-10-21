"""Disposable Phase 5 real-model persistence/rebuild audit. No provider I/O.
Run with --output for a retained report; all application writes are temporary.
"""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from unittest.mock import patch


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=list).encode()).hexdigest()


def isolated(root):
    from app.core.config import settings, LiveSettings
    from app.core import registry as reg
    from app.ingestion import indexer
    root = root.resolve(strict=True)
    assert root.parent == Path('/tmp') and root.name.startswith('phase5-')
    paths = [reg.ROOT, settings.app_data_directory, settings.db_path, indexer.DB_PATH,
             settings.upload_directory, settings.document_directory]
    for p in paths:
        assert p.resolve().is_relative_to(root) and p.resolve() != root, 'Storage isolation failed'
    assert LiveSettings.from_env().free_only and not LiveSettings.from_env().enabled
    return [str(p.resolve()) for p in paths]


def registry_rows():
    from app.core import registry as reg
    with reg.connect() as db:
        return {t: [dict(row) for row in db.execute('SELECT * FROM '+t+' ORDER BY id')]
                for t in ('documents', 'versions', 'calls', 'allowance', 'requests')}


def vectors_inventory():
    from app.ingestion import indexer
    client = indexer.get_client()
    result = {}
    for c in client.list_collections():
        collection = client.get_collection(c.name, embedding_function=None)
        records = collection.get(include=['documents', 'metadatas', 'embeddings'])
        rows = sorted([(cid, records['documents'][i], records['metadatas'][i],
                        list(map(float, records['embeddings'][i]))) for i, cid in enumerate(records['ids'])])
        result[c.name] = {'metadata': collection.metadata, 'rows_hash': digest(rows), 'count': len(rows)}
    return result


def worker(stage, root):
    paths = isolated(root)
    from app.core import registry as reg
    from app.core.config import settings
    from app.ingestion import lifecycle as life, indexer, parsers
    from app.rag import embeddings, retriever
    manifest = root / 'manifest.json'
    if stage == 'write':
        from huggingface_hub import try_to_load_from_cache
        cached = try_to_load_from_cache(settings.embedding_model, 'config.json', revision=settings.embedding_revision)
        assert isinstance(cached, str) and Path(cached).is_file(), 'Pinned model config unavailable locally'
        assert settings.embedding_revision in Path(cached).parts, 'Cache revision differs from pin'
        reg.initialize()
        from starlette.datastructures import UploadFile
        def ingest(name, text, did=None, expected=None):
            f = UploadFile(io.BytesIO(text.encode()), filename=name)
            try:
                item = life.ingest(f, did, expected)
            finally:
                f.file.close()
            assert item['status'] == 'ready', item.get('error', item['status'])
            return item
        old = ingest('annual leave old.txt', 'SUPERSEDED: Annual leave is eleven days.')
        active = ingest('annual leave updated नीति.md', 'CURRENT: Annual leave is twenty days. Contact People Operations for leave requests.', old['document_id'], old['id'])
        deleted = ingest('retired expense.txt', 'DELETED: Expense receipts are due in thirteen days.')
        life.delete(deleted['document_id'], deleted['id'])
        other = ingest('support hours.txt', 'CURRENT: IT support is available Monday through Friday from nine until five.')
        found = life.search('What is the annual leave entitlement?')
        assert {h['version_id'] for h in found['hits']} == {active['id'], other['id']}
        model = embeddings.get_embedding_model()
        assert str(model.device) == 'cpu'
        # Rebuild exercises missing-index recovery, not only the reuse shortcut.
        # All mutable paths were verified above, before this disposable deletion.
        before = vectors_inventory()
        indexer.get_client().delete_collection(active['index_name'])
        data = {'writer_pid': os.getpid(), 'active': [active, other],
                'inactive_ids': [old['id'], deleted['id']], 'registry_hash': digest(registry_rows()),
                'raw_hashes': {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in (reg.ROOT/'raw').iterdir()},
                'expected_collections': before, 'missing_collection': active['index_name'],
                'storage_paths': paths, 'model': settings.embedding_model,
                'revision': settings.embedding_revision, 'dimension': settings.embedding_dimension,
                'device': str(model.device), 'local_cache_revision_verified': True}
        manifest.write_text(json.dumps(data))
        return {'stage': stage, 'pid': os.getpid(), 'active_versions': [active['id'], other['id']],
                'real_embeddings': True, 'missing_index_for_rebuild': active['index_name']}
    data = json.loads(manifest.read_text())
    assert digest(registry_rows()) == data['registry_hash']
    assert {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in (reg.ROOT/'raw').iterdir()} == data['raw_hashes']
    if stage == 'after-preview':
        inventory = vectors_inventory()
        assert data['missing_collection'] not in inventory
        assert inventory == {k: v for k, v in data['expected_collections'].items() if k != data['missing_collection']}
        return {'stage': stage, 'preview_changed_registry_raw_or_vectors': False}
    inventory = vectors_inventory()
    assert set(inventory) == set(data['expected_collections'])
    # Embeddings regenerated on CPU may differ at tiny floating-point precision;
    # compare exact stored provenance/text and validate every vector separately.
    for item in data['active']:
        chunks = indexer.chunk_records(life._chunks(item))
        c = indexer.get_client().get_collection(item['index_name'], embedding_function=None)
        assert indexer.verify_records(c, chunks) == {x['chunk_id'] for x in chunks}
    if stage == 'after-apply':
        data['persisted_inventory'] = inventory
        manifest.write_text(json.dumps(data))
        return {'stage': stage, 'registry_and_raw_preserved': True, 'active_indexes_verified': True,
                'recovered_missing_collection': data['missing_collection']}
    assert stage == 'read' and os.getpid() != data['writer_pid']
    actual_query_embeddings = retriever.embed_texts
    query_count = 0
    def query(texts):
        nonlocal query_count
        query_count += len(texts)
        return actual_query_embeddings(texts)
    from chromadb.api.models.Collection import Collection
    from chromadb.api.client import Client
    # Fail, rather than silently ingest/rebuild, if retrieval tries any write API.
    forbidden = AssertionError('Fresh reader attempted ingestion/index mutation')
    with patch.object(life, 'ingest', side_effect=forbidden), patch.object(life, 'activate', side_effect=forbidden), \
         patch.object(parsers, 'parse', side_effect=forbidden), patch.object(indexer, 'index_documents', side_effect=forbidden), \
         patch.object(indexer, 'index_chunks', side_effect=forbidden), patch.object(indexer, 'embed_texts', side_effect=forbidden), \
         patch.object(Client, 'create_collection', side_effect=forbidden), patch.object(Client, 'get_or_create_collection', side_effect=forbidden), \
         patch.object(Collection, 'add', side_effect=forbidden), patch.object(Collection, 'upsert', side_effect=forbidden), \
         patch.object(Collection, 'update', side_effect=forbidden), patch.object(Collection, 'modify', side_effect=forbidden), \
         patch.object(retriever, 'embed_texts', side_effect=query):
        found = life.search('What is the current annual leave entitlement?')
    expected = {i['id']: i for i in data['active']}
    assert {h['version_id'] for h in found['hits']} == set(expected)
    assert query_count == len(expected)
    for h in found['hits']:
        item = expected[h['version_id']]
        ch = {c.id: c for c in life._chunks(item)}[h['id']]
        assert (h['document_id'], h['sha256'], h['filename'], h['text'], h['page'], h['section']) == (
            item['document_id'], item['sha256'], item['filename'], ch.page_content, ch.metadata['page'], ch.metadata['section'])
    assert not set(data['inactive_ids']) & {h['version_id'] for h in found['hits']}
    assert vectors_inventory() == data['persisted_inventory']
    assert digest(registry_rows()) == data['registry_hash']
    return {'stage': stage, 'writer_pid': data['writer_pid'], 'reader_pid': os.getpid(),
            'query_embeddings_real': query_count, 'device': str(embeddings.get_embedding_model().device),
            'registry_and_index_inventory_unchanged': True, 'reingest_and_mutation_guards_passed': True,
            'active_provenance_verified': True, 'deleted_superseded_excluded': True,
            'hit_ids': [h['id'] for h in found['hits']], 'live_calls': 0}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=Path)
    p.add_argument('--worker', choices=['write', 'after-preview', 'after-apply', 'read'])
    p.add_argument('--root', type=Path)
    args = p.parse_args()
    if args.worker:
        print(json.dumps(worker(args.worker, args.root), sort_keys=True))
        return
    assert args.output and not args.output.exists(), 'Choose a new evidence path'
    report = {'scope': 'disposable real CPU embedding/persistent Chroma audit', 'steps': [], 'completed': False}
    with tempfile.TemporaryDirectory(prefix='phase5-', dir='/tmp') as folder:
        root = Path(folder)
        (root/'guard').mkdir()
        (root/'guard/sitecustomize.py').write_text("import socket\ndef denied(*args, **kwargs):\n    raise RuntimeError('Offline audit: network forbidden')\nsocket.socket.connect=denied\nsocket.create_connection=denied\n")
        backend = Path(__file__).resolve().parents[1]
        env = {**os.environ, 'PYTHONPATH': str(root/'guard')+os.pathsep+str(backend),
               'APP_DATA_DIRECTORY': str(root/'runtime'), 'CHROMA_DB_PATH': str(root/'chroma'),
               'UPLOAD_DIRECTORY': str(root/'uploads'), 'DOCUMENT_DIRECTORY': str(root/'documents'),
               'HF_HUB_OFFLINE': '1', 'TRANSFORMERS_OFFLINE': '1', 'ANONYMIZED_TELEMETRY': 'false',
               'FREE_ONLY': 'true', 'LIVE_LLM_ENABLED': 'false', 'LANGCHAIN_TRACING_V2': 'false', 'LANGSMITH_TRACING': 'false'}
        def run(arguments):
            command = [sys.executable, '-m', *arguments]
            result = subprocess.run(command, env=env, capture_output=True, text=True)
            step = {'command': command, 'exit_code': result.returncode,
                    'stdout': result.stdout, 'stderr': result.stderr}
            report['steps'].append(step)
            args.output.write_text(json.dumps(report, indent=2))
            if result.returncode:
                raise RuntimeError('Phase 5 subprocess failed; see evidence report')
        def phase(name):
            run(['scripts.audit_phase5', '--worker', name, '--root', str(root)])
        phase('write')
        # A new process asserts all storage paths again immediately before each
        # maintenance invocation; environmental paths are identical and absolute.
        phase('after-preview')
        report['isolation'] = json.loads((root/'manifest.json').read_text())['storage_paths']
        run(['app.ingestion.maintenance', 'rebuild'])
        phase('after-preview')
        run(['app.ingestion.maintenance', 'rebuild', '--apply'])
        phase('after-apply')
        phase('read')
        report.update(completed=True, model=json.loads((root/'manifest.json').read_text())['model'],
                      revision=json.loads((root/'manifest.json').read_text())['revision'],
                      no_provider_calls=True, disposable_storage_removed_on_exit=True)
    args.output.write_text(json.dumps(report, indent=2))
    print(json.dumps({'completed': True, 'steps': len(report['steps']), 'output': str(args.output)}))


if __name__ == '__main__':
    main()
