"""Current local workflow with real cached embeddings, isolated services and data."""
import argparse
import hashlib
import ipaddress
import json
import math
import os
from pathlib import Path
import runpy
import socket
import sqlite3
import subprocess
import sys
import tempfile
import time
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[2]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def preserve():
    """Read-only production inventory; never serialize private environment contents."""
    from dotenv import dotenv_values
    values = dotenv_values(ROOT/'.env', interpolate=False)
    def configured(name, default):
        p = Path(values.get(name) or default).expanduser()
        return p if p.is_absolute() else ROOT/p
    runtime = configured('APP_DATA_DIRECTORY', 'backend/data/runtime')
    bases = [ROOT/'backend/benchmark', runtime, configured('CHROMA_DB_PATH', 'backend/data/chroma_db'),
             configured('UPLOAD_DIRECTORY', 'backend/data/uploads'), ROOT/'.private', ROOT/'docs/evidence']
    # Compare logical SQLite state rather than volatile journal/lock files.
    files = {str(p): digest(p) for base in bases for p in base.rglob('*') if p.is_file()
             and p.name not in {'registry.sqlite3', 'registry.sqlite3-wal', 'registry.sqlite3-shm', 'backend.lock'}}
    tables = {}
    dbpath = runtime/'registry.sqlite3'
    if dbpath.exists():
        with sqlite3.connect(dbpath.as_uri()+'?mode=ro', uri=True) as db:
            for name in ('calls', 'allowance', 'requests', 'documents', 'versions'):
                tables[name] = hashlib.sha256(json.dumps(list(db.execute('SELECT * FROM '+name+' ORDER BY id'))).encode()).hexdigest()
    return files, tables, (ROOT/'.env').read_bytes()


def local_network_only(events):
    """Allow real loopback/IPC, reject outbound networking even if a gate regresses."""
    def audit(event, args):
        if event not in ('socket.connect', 'socket.getaddrinfo'):
            return
        address = args[1] if event == 'socket.connect' else args[0]
        host = address[0] if isinstance(address, tuple) else address
        if isinstance(host, str) and (host.startswith('/') or host == 'localhost'):
            return
        try:
            allowed = ipaddress.ip_address(host).is_loopback
        except ValueError:
            allowed = False
        if not allowed:
            with events.open('a') as out:
                out.write('non_loopback_network_attempt_blocked\n')
            raise RuntimeError('Verification forbids non-loopback networking')
    sys.addaudithook(audit)


def service(kind, port, events):
    local_network_only(events)
    if kind == 'backend':
        from app.llm import azure_openai
        def forbidden(*args, **kwargs):
            with events.open('a') as out:
                out.write('provider_adapter_entry_blocked\n')
            raise AssertionError('Provider forbidden in local verification')
        azure_openai.generate = forbidden  # Safety sentinel only; retrieval is completely real.
        sys.argv = ['uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', str(port), '--workers', '1']
        runpy.run_module('uvicorn', run_name='__main__')
    else:
        sys.argv = ['streamlit', 'run', str(ROOT/'frontend/streamlit_app.py'), '--server.address', '127.0.0.1',
                    '--server.port', str(port), '--server.headless', 'true', '--browser.gatherUsageStats', 'false']
        runpy.run_module('streamlit', run_name='__main__')


def free_port():
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        return sock.getsockname()[1]


def verify(output):
    import httpx
    if output.exists():
        raise ValueError('Choose a new evidence filename; existing evidence is preserved')
    before = preserve()
    report = {'scope': 'Current-version disposable local workflow only; no live A/B/C verification',
              'started_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
              'source_hashes': {str(p.relative_to(ROOT)): digest(p) for base in ('backend/app', 'frontend')
                                for p in sorted((ROOT/base).rglob('*.py'))},
              'runner_sha256': digest(Path(__file__)), 'steps': [], 'passed': False, 'defects': []}
    processes = []
    with tempfile.TemporaryDirectory(prefix='current-local-workflow-') as temporary:
        task = Path(temporary)
        report['temporary_root'] = temporary
        backend_port, frontend_port = free_port(), free_port()
        while frontend_port == backend_port:
            frontend_port = free_port()
        base = f'http://127.0.0.1:{backend_port}'
        front = f'http://127.0.0.1:{frontend_port}'
        env = {**os.environ, 'PYTHONPATH': str(ROOT/'backend'), 'PYTHONDONTWRITEBYTECODE': '1',
               'APP_DATA_DIRECTORY': str(task/'runtime'), 'CHROMA_DB_PATH': str(task/'chroma'),
               'UPLOAD_DIRECTORY': str(task/'uploads'), 'DOCUMENT_DIRECTORY': str(task/'documents'),
               'LLM_BACKEND': 'azure_openai', 'LIVE_LLM_ENABLED': 'false', 'FREE_ONLY': 'true',
               'AZURE_OPENAI_API_KEY': '', 'AZURE_OPENAI_ENDPOINT': '', 'AZURE_OPENAI_DEPLOYMENT': '',
               'AZURE_OPENAI_ALLOWANCE_FILE': str(task/'never-created-approval.json'),
               'HF_HUB_OFFLINE': '1', 'TRANSFORMERS_OFFLINE': '1', 'HF_HUB_DISABLE_TELEMETRY': '1',
               'ANONYMIZED_TELEMETRY': 'false', 'BACKEND_URL': base,
               'LANGCHAIN_TRACING_V2': 'false', 'LANGSMITH_TRACING': 'false'}
        events = task/'forbidden-events.log'
        log_path = task/'services.log'
        log = log_path.open('w+')
        chroma = None
        try:
            for kind, port in (('backend', backend_port), ('frontend', frontend_port)):
                command = [sys.executable, '-B', '-m', 'scripts.verify_local_workflow', '--service', kind,
                           '--port', str(port), '--events', str(events)]
                processes.append(subprocess.Popen(command, cwd=ROOT, env=env, stdout=log, stderr=log))
                report.setdefault('service_commands', []).append(command)
            with httpx.Client(base_url=base, timeout=180, trust_env=False) as api:
                for url in (base+'/health', front+'/_stcore/health'):
                    for _ in range(150):
                        try:
                            response = api.get(url, timeout=1)
                            if response.status_code == 200:
                                break
                        except httpx.HTTPError:
                            pass
                        if any(p.poll() is not None for p in processes):
                            raise AssertionError('Task service exited; inspect saved service log')
                        time.sleep(.2)
                    else:
                        raise AssertionError('Task service startup deadline exceeded')
                ready = api.get('/ready').json()
                assert not ready['live']['enabled'] and not ready['live']['configured_enabled']
                report['steps'].append({'step': 'isolated services', 'backend_health': 200, 'frontend_health': 200,
                                        'live_disabled': True, 'backend': base, 'frontend': front})
                # AppTest executes the actual frontend against this backend; HTTP is not mocked.
                os.environ.update(env)
                local_network_only(events)
                from streamlit.testing.v1 import AppTest
                ui = AppTest.from_file(str(ROOT/'frontend/streamlit_app.py'), default_timeout=90)
                def render(stage, expected):
                    ui.run()
                    assert not ui.exception and not ui.error
                    assert len(ui.tabs) == 3
                    assert next(b for b in ui.button if b.label == 'Ask once').disabled
                    labels = [e.label for e in ui.expander]
                    for vid, state, active, fact in expected:
                        panel = next(e for e in ui.expander if e.label == f'Document | {state} | {vid}')
                        text = '\n'.join(str(t.value) for t in panel.text)
                        assert f'Active: {active}' in text
                        if fact:
                            assert fact in text
                        buttons = [b.label for b in panel.button]
                        assert ('Delete' in buttons) == (active == vid and state == 'ready')
                    report['steps'].append({'step': 'Documents interface '+stage, 'labels': labels,
                                            'exceptions': 0, 'errors': 0, 'ask_disabled': True})
                render('empty', [])
                fact1 = 'For project MARIGOLD-731, the calibration vault opens at 07:43 each Tuesday.'
                fact2 = 'For project MARIGOLD-731, the calibration vault opens at 16:29 each Thursday.'
                raw1 = ('# Fictional observatory\n'+fact1+'\n').encode()
                raw2 = ('# Fictional observatory revision\n'+fact2+'\n').encode()
                response = api.post('/documents', files={'files': ('Marigold fictional policy.md', raw1)})
                assert response.status_code == 201
                initial = response.json()['outcomes'][0]
                did, old = initial['document_id'], initial['id']
                assert initial['status'] == 'ready' and initial['sha256'] == hashlib.sha256(raw1).hexdigest()
                assert fact1 in '\n'.join(b['text'] for b in initial['blocks'])
                assert (task/'runtime/raw'/old).read_bytes() == raw1
                listing = api.get('/documents').json()['documents']
                assert listing[0]['active_version'] == old and listing[0]['deleted'] == 0
                # Inspect persisted real vectors/chunks, not a replacement embedding function.
                import chromadb
                chroma = chromadb.PersistentClient(path=str(task/'chroma'), settings=chromadb.Settings(anonymized_telemetry=False))
                def inspect(item, raw):
                    collection = chroma.get_collection(item['index_name'], embedding_function=None)
                    records = collection.get(include=['documents', 'metadatas', 'embeddings'])
                    metadata = collection.metadata
                    assert metadata['status'] == 'verified' and len(records['ids']) >= 1
                    for text, m, vector in zip(records['documents'], records['metadatas'], records['embeddings']):
                        assert m['version_id'] == item['id'] and m['document_id'] == did
                        assert m['document_sha256'] == hashlib.sha256(raw).hexdigest()
                        assert m['chunk_sha256'] == hashlib.sha256(text.encode()).hexdigest()
                        assert m['source'] == item['filename'] and m['page'] == 0 and m['section'] == 'text'
                        assert m['parser_version'] == item['parser_version']
                        assert raw.decode()[m['start_char']:m['end_char']] == text
                        assert len(vector) == metadata['embedding_dimension']
                        assert math.isclose(sum(float(x)**2 for x in vector), 1, abs_tol=.002)
                    return {'index': item['index_name'], 'chunk_ids': records['ids'], 'configuration': metadata,
                            'parser_version': item['parser_version'], 'real_unit_vectors_verified': True}
                report['steps'].append({'step': 'upload/extract/activate/index', 'http_status': 201,
                                        'document_id': did, 'version_id': old, 'sha256': initial['sha256'],
                                        'extracted_fact': fact1, **inspect(initial, raw1)})
                query = {'question': 'When does the calibration vault open for project MARIGOLD-731?',
                         'mode': 'B', 'request_id': str(uuid4())}
                def search(expected, fact):
                    response = api.post('/search', json=query)
                    assert response.status_code == 200
                    result = response.json()
                    if expected:
                        assert result['hits'] and all(h['version_id'] == expected for h in result['hits'])
                        assert all(h['document_id'] == did for h in result['hits'])
                        assert any(fact in h['text'] for h in result['hits'])
                        assert {s['version_id'] for s in result['snapshot']} == {expected}
                    else:
                        assert result['hits'] == [] and result['snapshot'] == []
                    return result
                report['steps'].append({'step': 'real cached CPU search', 'retrieval': search(old, fact1)})
                render('initial active', [(old, 'ready', old, fact1)])
                response = api.post(f'/documents/{did}/replace', params={'expected_version': old},
                                    files={'file': ('Marigold revised policy.md', raw2)})
                assert response.status_code == 200
                replacement = response.json(); new = replacement['id']
                assert replacement['status'] == 'ready' and new != old and replacement['document_id'] == did
                assert (task/'runtime/raw'/new).read_bytes() == raw2
                report['steps'].append({'step': 'successful replacement', 'http_status': 200,
                                        'version_id': new, **inspect(replacement, raw2), 'retrieval': search(new, fact2)})
                render('replacement active', [(old, 'ready', new, fact1), (new, 'ready', new, fact2)])
                response = api.post(f'/documents/{did}/replace', params={'expected_version': new},
                                    files={'file': ('Invalid replacement.pdf', b'%PDF-corrupt')})
                assert response.status_code == 200
                rejected = response.json(); bad = rejected['id']
                assert rejected['status'] == 'rejected' and rejected['index_name'] is None
                listing = api.get('/documents').json()['documents']
                assert all(v['active_version'] == new for v in listing)
                report['steps'].append({'step': 'invalid replacement preserves usable version', 'http_status': 200,
                                        'version_status': 'rejected', 'version_id': bad,
                                        'error': rejected['error'], 'retrieval': search(new, fact2)})
                render('invalid replacement', [(old, 'ready', new, fact1), (new, 'ready', new, fact2),
                                               (bad, 'rejected', new, None)])
                # Exercise the real Documents delete action, not just an API deletion.
                next(c for c in ui.checkbox if c.key == 'd'+new).check().run()
                panel = next(e for e in ui.expander if e.label.endswith(new))
                next(b for b in panel.button if b.label == 'Delete').click().run()
                assert not ui.exception and not ui.error
                listing = api.get('/documents').json()['documents']
                assert len(listing) == 3
                assert all(v['status'] == 'deleted' and v['active_version'] is None and v['deleted'] for v in listing)
                report['steps'].append({'step': 'delete through Documents interface', 'all_versions_deleted': True,
                                        'retrieval': search(None, None)})
                render('deleted history', [(old, 'deleted', None, fact1), (new, 'deleted', None, fact2),
                                           (bad, 'deleted', None, None)])
                with sqlite3.connect((task/'runtime/registry.sqlite3').as_uri()+'?mode=ro', uri=True) as db:
                    counts = {t: db.execute('SELECT COUNT(*) FROM '+t).fetchone()[0] for t in ('calls', 'allowance', 'requests')}
                assert counts == {'calls': 0, 'allowance': 0, 'requests': 0}
                assert not (task/'never-created-approval.json').exists()
                assert not events.exists() or not events.read_text()
                report.update(passed=True, provider_calls=0, forbidden_events=0, isolated_ledger_counts=counts,
                              main_workflow_embedding_doubles=False, downloads=False,
                              ui_scope='Real Streamlit service health plus AppTest running unchanged frontend against real backend; API multipart uploads/replacements; actual UI delete')
        except BaseException as exc:
            report['failure_type'] = type(exc).__name__
            raise
        finally:
            if chroma is not None:
                chroma._system.stop()
            for p in processes:
                if p.poll() is None:
                    p.terminate()
            for p in processes:
                try:
                    p.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    p.kill(); p.wait()
            report['task_service_exit_codes'] = [p.returncode for p in processes]
            log.close()
            report['service_log'] = log_path.read_text()
            after = preserve()
            report['preservation'] = {'existing_files_checked': len(before[0]),
                'existing_files_unchanged': all(after[0].get(p) == h for p, h in before[0].items()),
                'production_tables_unchanged': before[1] == after[1], 'root_env_bytes_unchanged': before[2] == after[2]}
            assert all(report['preservation'][k] for k in ('existing_files_unchanged', 'production_tables_unchanged', 'root_env_bytes_unchanged'))
            with output.open('x') as out:
                json.dump(report, out, indent=2)
    report['temporary_storage_removed'] = not Path(temporary).exists()
    # Finalize only this newly created task artifact after temporary storage cleanup.
    output.write_text(json.dumps(report, indent=2))
    print(json.dumps({k: report[k] for k in ('passed', 'provider_calls', 'temporary_storage_removed', 'preservation')}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--service', choices=['backend', 'frontend'])
    parser.add_argument('--port', type=int)
    parser.add_argument('--events', type=Path)
    args = parser.parse_args()
    if args.service:
        service(args.service, args.port, args.events)
    elif args.output:
        verify(args.output)
    else:
        parser.error('--output required')


if __name__ == '__main__':
    main()
