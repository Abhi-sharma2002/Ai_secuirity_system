"""Offline configuration checks: temporary dummy values, no model downloads/provider I/O."""
import contextlib
import io
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from app.core.environment import ENV_FILE, PROJECT_ROOT, load_environment, resolve_path
from app.core.config import LiveSettings
from app.llm import client as live


class EnvironmentTests(unittest.TestCase):
    def test_dotenv_loading_preserves_process_values_and_does_not_interpolate(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / '.env'
            path.write_text('GROQ_API_KEY=dummy-file-key\nGROQ_MODEL=dummy-file-model\n'
                            'FREE_ONLY=true\nLIVE_LLM_ENABLED=false\n'
                            'FREE_ALLOWANCE_FILE=literal-${UNRELATED_TOKEN}\n')
            before = path.read_bytes()
            with patch.dict(os.environ, {'GROQ_API_KEY': 'dummy-process-key',
                                         'GROQ_MODEL': '', 'UNRELATED_TOKEN': 'dummy-unrelated'}, clear=True):
                load_environment(path)
                self.assertEqual(os.environ['GROQ_API_KEY'], 'dummy-process-key')
                self.assertEqual(os.environ['GROQ_MODEL'], '')
                self.assertEqual(os.environ['LIVE_LLM_ENABLED'], 'false')
                self.assertEqual(os.environ['FREE_ALLOWANCE_FILE'], 'literal-${UNRELATED_TOKEN}')
            self.assertEqual(before, path.read_bytes())

    def test_import_and_paths_work_from_root_backend_and_unrelated_directory(self):
        code = '''
from app.core.environment import ENV_FILE, PROJECT_ROOT
from app.core.config import settings, LiveSettings
from app.core import registry
assert ENV_FILE == PROJECT_ROOT / '.env'
assert settings.db_path == PROJECT_ROOT / 'temporary-index'
assert settings.app_data_directory == PROJECT_ROOT / 'temporary-runtime'
assert registry.ROOT == settings.app_data_directory
assert settings.max_file_size == 12345
config = LiveSettings.from_env()
assert config.api_key == 'dummy-process-key'
assert config.model == 'dummy-model'
assert not config.enabled and config.free_only
print('offline import/path/precedence check passed')
'''
        with tempfile.TemporaryDirectory() as folder:
            for cwd in (PROJECT_ROOT, PROJECT_ROOT/'backend', Path(folder)):
                env = {**os.environ, 'PYTHONPATH': str(PROJECT_ROOT/'backend'),
                       'CHROMA_DB_PATH': 'temporary-index', 'APP_DATA_DIRECTORY': 'temporary-runtime',
                       'MAX_DOCUMENT_BYTES': '12345', 'GROQ_API_KEY': 'dummy-process-key',
                       'GROQ_MODEL': 'dummy-model', 'LIVE_LLM_ENABLED': 'false', 'FREE_ONLY': 'true'}
                result = subprocess.run([sys.executable, '-c', code], cwd=cwd, env=env,
                                        capture_output=True, text=True, timeout=20)
                self.assertEqual(result.returncode, 0, 'Offline import/path/precedence check failed')
                self.assertIn('check passed', result.stdout)

    def test_temporary_file_settings_reach_backend_and_registry(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / '.env'
            path.write_text('MAX_DOCUMENT_BYTES=54321\nAPP_DATA_DIRECTORY=temporary-data\n'
                            'LLM_REQUEST_TIMEOUT_SECONDS=12.5\nFREE_ONLY=true\nLIVE_LLM_ENABLED=false\n')
            code = '''
import os
from pathlib import Path
from app.core.environment import load_environment, PROJECT_ROOT
for name in ('MAX_DOCUMENT_BYTES','APP_DATA_DIRECTORY','LLM_REQUEST_TIMEOUT_SECONDS','FREE_ONLY','LIVE_LLM_ENABLED'):
    os.environ.pop(name, None)
load_environment(Path(os.environ['TEST_ENV_FILE']))
from app.core.config import settings, LiveSettings
from app.core import registry
assert settings.max_file_size == 54321
assert registry.ROOT == PROJECT_ROOT/'temporary-data'
assert LiveSettings.from_env().request_timeout_seconds == 12.5
'''
            result = subprocess.run([sys.executable, '-c', code], capture_output=True,
                                    env={**os.environ, 'PYTHONPATH': str(PROJECT_ROOT/'backend'),
                                         'TEST_ENV_FILE': str(path)}, timeout=20)
            self.assertEqual(result.returncode, 0, 'Temporary .env settings did not reach backend')

    def test_live_flags_credentials_timeout_validation_and_redaction(self):
        with patch.dict(os.environ, {'FREE_ONLY': 'true', 'LIVE_LLM_ENABLED': 'false'}, clear=True):
            config = LiveSettings.from_env()
            self.assertEqual(config.api_key, '')
            self.assertFalse(config.enabled)
            with self.assertRaisesRegex(live.LiveBlocked, 'disabled'):
                live.approval()
        with patch.dict(os.environ, {'FREE_ONLY': 'true', 'LIVE_LLM_ENABLED': 'true',
                                    'GROQ_API_KEY': 'dummy-sensitive-key', 'GROQ_MODEL': '   '}, clear=True):
            with self.assertRaisesRegex(live.LiveBlocked, 'GROQ_API_KEY and GROQ_MODEL') as caught:
                live.approval()
            self.assertNotIn('dummy-sensitive-key', str(caught.exception))
            os.environ['GROQ_MODEL'] = 'dummy-model'
            self.assertNotIn('dummy-sensitive-key', repr(LiveSettings.from_env()))
            with self.assertRaisesRegex(live.LiveBlocked, 'FREE_ALLOWANCE_FILE'):
                live.approval()  # A key/model alone never prove free allowance.
            os.environ['LLM_REQUEST_TIMEOUT_SECONDS'] = 'nan'
            with self.assertRaisesRegex(live.LiveBlocked, 'finite and positive'):
                live.approval()
        for name in ('FREE_ONLY', 'LIVE_LLM_ENABLED'):
            with patch.dict(os.environ, {name: 'invalid-dummy-flag'}, clear=True):
                with self.assertRaisesRegex(live.LiveBlocked, 'must be true or false'):
                    live.approval()
        with patch.dict(os.environ, {'FREE_ONLY': 'false', 'LIVE_LLM_ENABLED': 'false'}, clear=True):
            with self.assertRaisesRegex(live.LiveBlocked, 'FREE_ONLY=true'):
                live.approval()

    def test_disabled_generation_screening_and_evaluation_never_reach_provider(self):
        from app.rag.assistant import respond
        from app.evaluation import experiment
        provider = MagicMock()
        evidence = {'hits': [{'id': 'dummy-source', 'text': 'Dummy policy evidence.'}],
                    'snapshot': [], 'omitted_ids': []}
        with patch.dict(os.environ, {'FREE_ONLY': 'true', 'LIVE_LLM_ENABLED': 'false',
                                     'GROQ_API_KEY': 'dummy-key', 'GROQ_MODEL': 'dummy-model'}, clear=True), \
             patch.dict(sys.modules, {'langchain_groq': provider}), \
             patch('socket.socket.connect', side_effect=AssertionError('Outbound network forbidden')):
            for stage in ('generation', 'screening'):
                with self.assertRaises(live.LiveBlocked):
                    live.call([], {}, stage, 'dummy-reservation')
            for mode in 'ABC':
                self.assertEqual(respond('Dummy question?', mode, initial=evidence)['status'], 'live_blocked')
            with patch.object(experiment, 'prepare') as prepare, contextlib.redirect_stdout(io.StringIO()):
                with self.assertRaises(live.LiveBlocked):
                    experiment.run('offline-only', 'development', 'paired', 1, 42, True, 'development-01')
                prepare.assert_not_called()
            provider.ChatGroq.assert_not_called()

    def test_frontend_does_not_import_backend_or_load_secret_file(self):
        source = (PROJECT_ROOT/'frontend/streamlit_app.py').read_text()
        self.assertNotIn('GROQ_API_KEY', source)
        self.assertNotIn('load_dotenv', source)
        self.assertNotIn('from app.', source)


if __name__ == '__main__':
    unittest.main()
