"""Start the local app; optional gated live answering, never automatic queries."""
import argparse
import importlib.util
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parent


def service_environments(parent, live_answers=False, paid_azure_test=False):
    if paid_azure_test:
        raise ValueError('Paid launch mode is disabled by the standing trial-credit-only project scope')
    backend = parent.copy()
    backend.update(PYTHONPATH=str(ROOT/'backend'), BACKEND_URL='http://127.0.0.1:8000',
                   LIVE_LLM_ENABLED='true' if live_answers else 'false', FREE_ONLY='true')
    frontend = backend.copy()
    frontend['LIVE_LLM_ENABLED'] = 'false'
    return backend, frontend


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='Check local dependencies without starting services')
    parser.add_argument('--live-answers', action='store_true',
                        help='Enable backend answering only within its existing valid allowance; sends no query')
    parser.add_argument('--paid-azure-test', action='store_true',
                        help='Retired option; rejected under the standing trial-credit-only scope')
    args = parser.parse_args()
    if args.paid_azure_test:
        parser.error('--paid-azure-test is disabled: trial credits only, no out-of-pocket authorization')
    missing = [name for name in ('uvicorn', 'streamlit', 'fastapi', 'httpx', 'langchain_core', 'chromadb', 'sentence_transformers')
               if importlib.util.find_spec(name) is None]
    if missing:
        parser.exit(1, 'Missing dependencies: '+', '.join(missing)+'\nUse the existing .venv and backend/requirements.txt.\n')
    if not (ROOT/'.env').is_file():
        parser.exit(1, 'Create .env from .env.example and enter configuration locally first.\n')
    if args.check:
        print('Local app dependencies and .env present. No services or provider requests started.')
        return
    # Only these children are managed; never stop an unrelated existing service.
    backend_env, frontend_env = service_environments(os.environ, args.live_answers, args.paid_azure_test)
    commands = [
        [sys.executable, '-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', '8000', '--workers', '1'],
        [sys.executable, '-m', 'streamlit', 'run', str(ROOT/'frontend/streamlit_app.py'),
         '--server.address', '127.0.0.1', '--server.port', '8501', '--server.headless', 'true',
         '--browser.gatherUsageStats', 'false'],
    ]
    children = []
    def stop(_signal, _frame):
        raise KeyboardInterrupt
    signal.signal(signal.SIGTERM, stop)
    try:
        for command, env in zip(commands, (backend_env, frontend_env)):
            children.append(subprocess.Popen(command, cwd=ROOT, env=env))
        status = 'Backend live answering requested; every call requires valid remaining allowance.' if args.live_answers else 'Live answering disabled.'
        print('Document Assistant: http://127.0.0.1:8501\n'+status+' Ctrl+C stops both services.', flush=True)
        while all(child.poll() is None for child in children):
            time.sleep(0.5)
        failed = next(child.returncode for child in children if child.returncode is not None)
        return failed or 1
    except KeyboardInterrupt:
        return 0
    finally:
        for child in children:
            if child.poll() is None:
                child.terminate()
        for child in children:
            try:
                child.wait(timeout=10)
            except subprocess.TimeoutExpired:
                child.kill()
                child.wait()


if __name__ == '__main__':
    sys.exit(main())
