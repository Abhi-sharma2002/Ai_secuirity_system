"""Actual isolated API/UI and cached CPU retrieval verification; no external calls."""
import argparse
import hashlib
import ipaddress
import json
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
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'backend'))


def local_network_only(events):
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
            with events.open('a') as handle:
                handle.write('outbound_attempt_blocked\n')
            raise RuntimeError('Offline verification forbids outbound networking')
    sys.addaudithook(audit)


def free_port():
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        return sock.getsockname()[1]


def service(kind, port, events):
    local_network_only(events)
    if kind == 'backend':
        sys.argv = ['uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', str(port), '--workers', '1']
        runpy.run_module('uvicorn', run_name='__main__')
    else:
        sys.argv = ['streamlit', 'run', str(ROOT / 'frontend/streamlit_app.py'), '--server.address', '127.0.0.1',
                    '--server.port', str(port), '--server.headless', 'true', '--browser.gatherUsageStats', 'false']
        runpy.run_module('streamlit', run_name='__main__')


def inventory():
    paths = [p for name in ('backend/benchmark', 'backend/benchmark_v3', 'results', '.private')
             for p in (ROOT / name).rglob('*') if p.is_file()]
    hashes = {str(p): hashlib.sha256(p.read_bytes()).digest() for p in paths}
    env = ROOT / '.env'
    stat = (env.stat().st_size, env.stat().st_mtime_ns) if env.exists() else None
    return hashes, stat


def verify(output):
    import httpx
    if output.exists():
        raise ValueError('Choose a new output filename; existing evidence is preserved')
    before = inventory()
    result = {'scope': 'Isolated local API/UI/retrieval verification; no live defense effectiveness measurement', 'passed': False}
    processes = []
    with tempfile.TemporaryDirectory(prefix='v3-local-') as temporary:
        task = Path(temporary)
        back, front = free_port(), free_port()
        while front == back:
            front = free_port()
        base = f'http://127.0.0.1:{back}'
        events = task / 'outbound-events.log'
        env = {**os.environ, 'PYTHONPATH': os.pathsep.join([str(ROOT / 'backend'), str(ROOT)]), 'PYTHONDONTWRITEBYTECODE': '1',
               'APP_DATA_DIRECTORY': str(task / 'runtime'), 'CHROMA_DB_PATH': str(task / 'chroma'),
               'UPLOAD_DIRECTORY': str(task / 'uploads'), 'DOCUMENT_DIRECTORY': str(task / 'documents'),
               'BACKEND_URL': base, 'LIVE_LLM_ENABLED': 'false', 'FREE_ONLY': 'true', 'LLM_BACKEND': 'azure_openai',
               'OPENROUTER_API_KEY': '', 'AZURE_OPENAI_API_KEY': '',
               'AZURE_OPENAI_ENDPOINT': 'https://synthetic.openai.azure.com', 'AZURE_OPENAI_DEPLOYMENT': 'gpt-5-mini',
               'AZURE_OPENAI_ALLOWANCE_FILE': str(task / 'never-created.json'),
               'HF_HUB_OFFLINE': '1', 'TRANSFORMERS_OFFLINE': '1', 'HF_HUB_DISABLE_TELEMETRY': '1',
               'ANONYMIZED_TELEMETRY': 'False', 'CHUNK_SIZE': '1000', 'CHUNK_OVERLAP': '150',
               'STREAMLIT_BROWSER_GATHER_USAGE_STATS': 'false', 'LANGCHAIN_TRACING_V2': 'false', 'LANGSMITH_TRACING': 'false'}
        try:
            with (task / 'services.log').open('w') as log:
                for kind, port in (('backend', back), ('frontend', front)):
                    processes.append(subprocess.Popen([sys.executable, '-B', str(Path(__file__).resolve()),
                        '--service', kind, '--port', str(port), '--events', str(events)], cwd=ROOT, env=env, stdout=log, stderr=log))
                with httpx.Client(base_url=base, timeout=120, trust_env=False) as api:
                    for url in (base + '/health', f'http://127.0.0.1:{front}/_stcore/health'):
                        for _ in range(150):
                            try:
                                if api.get(url, timeout=1).status_code == 200:
                                    break
                            except httpx.HTTPError:
                                pass
                            if any(p.poll() is not None for p in processes):
                                raise AssertionError('A task service exited before readiness')
                            time.sleep(.2)
                        else:
                            raise AssertionError('Local service startup deadline exceeded')
                    result.update(api_health=True, streamlit_health=True)
                    ready = api.get('/ready').json()
                    assert ready['live']['enabled'] is False
                    fact = 'The fictional ORCHID-LOCAL policy grants 3 study leave days.'
                    upload = api.post('/documents', files={'files': ('Fictional local policy.md', fact.encode())})
                    assert upload.status_code == 201
                    document = upload.json()['outcomes'][0]
                    assert document['status'] == 'ready'
                    did, vid = document['document_id'], document['id']
                    question = {'question': 'How many study leave days does ORCHID-LOCAL grant?', 'mode': 'B', 'request_id': str(uuid4())}
                    hits = api.post('/search', json=question).json()['hits']
                    assert any(fact in h['text'] and h['document_id'] == did for h in hits)
                    result.update(actual_upload_and_cpu_index=True, actual_local_search=True)
                    # Execute the actual current frontend against the running backend.
                    os.environ.update(env)
                    local_network_only(events)
                    from streamlit.testing.v1 import AppTest
                    ui = AppTest.from_file(str(ROOT / 'frontend/streamlit_app.py'), default_timeout=120).run()
                    assert not ui.exception and not ui.error
                    workspace = next(r for r in ui.radio if r.label == 'Workspace')
                    assert workspace.value == 'Documents'
                    workspace.set_value('Ask / compare').run()
                    assert not ui.exception and not ui.error
                    next(t for t in ui.text_area if t.label == 'Question').input(question['question'])
                    next(b for b in ui.button if b.label == 'Search locally').click().run()
                    assert not ui.exception and not ui.error
                    # Ask intentionally shows source labels without raw passages.
                    assert any('Fictional local policy.md' in str(t.value) for t in ui.caption)
                    assert not any(fact in str(t.value) for t in ui.text)
                    next(r for r in ui.radio if r.label == 'Workspace').set_value('Search evidence').run()
                    next(t for t in ui.text_input if t.label == 'What fact are you looking for?').input(question['question'])
                    next(b for b in ui.button if b.label == 'Search locally').click().run()
                    assert not ui.exception and any(fact in str(t.value) for t in ui.text)
                    next(r for r in ui.radio if r.label == 'Workspace').set_value('Ask / compare').run()
                    next(r for r in ui.radio if r.label == 'Document handling').set_value('azure_openai').run()
                    assert next(b for b in ui.button if b.label == 'Ask once via Azure OpenAI').disabled
                    for mode in 'ABC':
                        next(s for s in ui.selectbox if s.label == 'Defense configuration').set_value(mode).run()
                        assert not ui.exception and next(b for b in ui.button if b.label == 'Ask once via Azure OpenAI').disabled
                        query = {**question, 'mode': mode, 'request_id': str(uuid4())}
                        a = api.post('/chat', json=query).json()
                        b = api.post('/chat', json=query).json()
                        assert a == b and a['status'] == 'live_blocked'
                    for name in ('Metrics / evaluation', 'Search evidence', 'Saved experiments', 'Assignment guide', 'Documents'):
                        next(r for r in ui.radio if r.label == 'Workspace').set_value(name).run()
                        assert not ui.exception and not ui.error
                    result.update(actual_ui_local_search=True, all_workspaces_render=True,
                                  abc_live_disabled=True, request_idempotency=True)
                    replacement = api.post(f'/documents/{did}/replace', params={'expected_version': vid},
                        files={'file': ('Invalid replacement.pdf', b'%PDF-corrupt')}).json()
                    assert replacement['status'] == 'rejected'
                    assert any(fact in h['text'] for h in api.post('/search', json=question).json()['hits'])
                    deleted = api.delete(f'/documents/{did}', params={'expected_version': vid})
                    assert deleted.status_code == 200
                    assert api.post('/search', json=question).json()['hits'] == []
                    result.update(invalid_replacement_preserves_evidence=True, logical_delete_excludes_retrieval=True)
                    with sqlite3.connect(task / 'runtime/registry.sqlite3') as db:
                        calls = db.execute('SELECT COUNT(*) FROM calls').fetchone()[0]
                        allowances = db.execute('SELECT COUNT(*) FROM allowance').fetchone()[0]
                    assert calls == 0 and allowances == 0
                    assert not events.exists() or not events.read_text()
                    result.update(passed=True, provider_calls=calls, allowance_rows_created=allowances,
                                  forbidden_network_events=0, embedding_doubles=False)
        except BaseException as exc:
            result['failure_type'] = type(exc).__name__
            raise
        finally:
            for process in processes:
                if process.poll() is None:
                    process.terminate()
            for process in processes:
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
            result['owned_services_stopped'] = all(p.poll() is not None for p in processes)
            result['datasets_results_private_state_unchanged'] = before == inventory()
            assert result['datasets_results_private_state_unchanged']
            with output.open('x') as handle:
                json.dump(result, handle, indent=2)
                handle.write('\n')
    print(json.dumps(result, indent=2))


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
