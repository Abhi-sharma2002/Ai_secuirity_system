"""Isolated local evaluation ingestion; no provider calls or application storage."""
import hashlib
import json
import os
from pathlib import Path
import re
from uuid import uuid4

from app.evaluation.simple_config import EvaluationError, ROOT


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def collection_path(store, identity):
    generation = identity.get('generation', '')
    if not isinstance(generation, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,100}', generation):
        raise EvaluationError('Invalid local evaluation index generation')
    return Path(store) / 'chroma' / generation


def embedding_identity():
    from app.rag.indexer import index_configuration
    return digest(index_configuration())


def prepare_store(data, config, store, *, progress=None):
    from huggingface_hub import constants as hub_settings
    if not hub_settings.HF_HUB_OFFLINE or os.getenv('TRANSFORMERS_OFFLINE') != '1':
        raise EvaluationError('Start local index preparation with HF_HUB_OFFLINE=1 and TRANSFORMERS_OFFLINE=1; downloads are disabled.')
    import chromadb
    from app.ingestion.parsers import parse, PARSER_VERSION
    from app.ingestion.chunker import chunk_documents
    from app.rag.embeddings import ProjectEmbeddings, validate_vectors

    store = Path(store)
    identity = {'manifest_sha256': hashlib.sha256((ROOT / 'backend/benchmark_v3/manifest.json').read_bytes()).hexdigest(),
                'config_sha256': digest(config), 'embedding_sha256': embedding_identity(), 'generation': uuid4().hex}
    path = collection_path(store, identity)
    records = []
    for number, fixture in enumerate(data['fixtures'], 1):
        source = ROOT / 'backend/benchmark_v3' / fixture['path']
        raw = source.read_bytes()
        if hashlib.sha256(raw).hexdigest() != fixture['sha256']:
            raise EvaluationError('Fixture changed during local evaluation ingestion')
        parsed = parse(raw, source.suffix)
        if parsed['status'] != 'parsed':
            raise EvaluationError('Evaluation fixture could not be completely parsed')
        for block_number, block in enumerate(parsed['blocks']):
            text = block['text']
            chunks = chunk_documents([{'document_id': fixture['fixture_id'], 'source': fixture['path'],
                                       'content': text, 'sha256': hashlib.sha256(text.encode()).hexdigest()}],
                                      config['chunk_size'], config['chunk_overlap'])
            for chunk in chunks:
                chunk['chunk_id'] = f'{fixture["fixture_id"]}_block_{block_number:03d}_{chunk["chunk_id"].rsplit("_", 1)[-1]}'
                chunk.update(fixture_sha256=fixture['sha256'], page=block['page'], section=block['section'],
                             parser_version=PARSER_VERSION)
                records.append(chunk)
        if progress and (number % 10 == 0 or number == len(data['fixtures'])):
            progress(f'Parsed {number}/{len(data["fixtures"])} fixture documents locally.')
    client = chromadb.PersistentClient(path=str(path), settings=chromadb.Settings(anonymized_telemetry=False))
    collection = client.create_collection('benchmark_v3', embedding_function=None,
                                         metadata={**identity, 'hnsw:space': 'cosine', 'expected_chunks': len(records)})
    embedding = ProjectEmbeddings()
    for start in range(0, len(records), 16):
        batch = records[start:start + 16]
        vectors = embedding.embed_documents([c['content'] for c in batch])
        validate_vectors(vectors, len(batch))
        collection.add(ids=[c['chunk_id'] for c in batch], documents=[c['content'] for c in batch], embeddings=vectors,
                       metadatas=[{k: v for k, v in c.items() if k not in {'content', 'chunk_id'}} for c in batch])
    saved = collection.get(include=['documents', 'metadatas'])
    expected = {c['chunk_id']: c for c in records}
    if set(saved['ids']) != set(expected) or collection.count() != len(records):
        raise EvaluationError('Local evaluation index contains missing or unexpected chunks')
    for cid, text, meta in zip(saved['ids'], saved['documents'], saved['metadatas']):
        record = expected[cid]
        if text != record['content'] or meta != {k: v for k, v in record.items() if k not in {'content', 'chunk_id'}}:
            raise EvaluationError('Local evaluation index differs from parsed fixture evidence')

    # Activate only a fully verified new generation. Preserve old, untracked cache
    # files by moving them to archive; git mv cannot move ignored local databases.
    old_file = store / 'identity.json'
    if old_file.exists():
        old = json.loads(old_file.read_text())
        old_path = collection_path(store, old)
        if not old_path.is_dir():
            raise EvaluationError('Existing evaluation identity has no index; refusing to replace it')
        archive = ROOT / 'archive/local_evaluation_stores' / f'{old["generation"]}-{uuid4().hex[:8]}'
        (archive / 'chroma').mkdir(parents=True)
        old_path.rename(archive / 'chroma' / old['generation'])
        old_file.rename(archive / 'identity.json')
    temporary = store / f'identity-{identity["generation"]}.json'
    with temporary.open('x') as handle:
        json.dump(identity, handle, indent=2)
        handle.write('\n')
        handle.flush()
        os.fsync(handle.fileno())
    temporary.rename(old_file)
    return {**identity, 'n_documents': len(data['fixtures']), 'n_chunks': len(records), 'provider_requests_made': 0}
