"""Synthetic SDK errors only; transport/socket guards and disposable ledger."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from app.llm import diagnostics
from app.core import environment
from backend.tests.llm import test_provider_endpoint as endpoint_tests


class ProviderDiagnosticsTests(unittest.TestCase):
    def exercise(self, **kwargs):
        return endpoint_tests.ProviderEndpointTests().exercise(401, **kwargs)

    def test_structured_authentication_error(self):
        record=self.exercise()
        self.assertEqual(record['http_status'],401)
        self.assertEqual(record['provider_error_type'],'authentication_error')
        self.assertEqual(record['provider_error_code'],'invalid_api_key')
        self.assertEqual(record['provider_error_message'],'Invalid API key')
        self.assertEqual(record['operational_outcome'],'failed')
        self.assertEqual(record['error'],'authentication_or_permission')

    def test_missing_and_non_json_error_body(self):
        for kwargs in ({'error_body':{}},{'non_json':True}):
            record=self.exercise(**kwargs)
            self.assertIsNone(record['provider_error_message'])
            self.assertIsNone(record['provider_error_code'])
            self.assertEqual(record['http_status'],401)

    def test_credential_echo_redacted_before_persistence(self):
        dummy='OFFLINE-DUMMY-CREDENTIAL-ONLY'
        record=self.exercise(error_body={'error':{'message':
            'Invalid API key '+dummy+' gsk_synthetic_secret123456789 key fragment ABCD cookie=session123',
            'type':'authentication_error','code':'invalid_api_key'},
            'ignored':'DO_NOT_PERSIST'})
        encoded=json.dumps(record)
        self.assertTrue(all(s not in encoded for s in (dummy,'synthetic_secret','ABCD','session123','DO_NOT_PERSIST')))
        self.assertIn('[REDACTED]',record['provider_error_message'])
        self.assertLessEqual(len(record['provider_error_message']),512)

    def test_diagnostic_failure_does_not_mask_authentication_error(self):
        with patch.object(diagnostics,'error_details',side_effect=RuntimeError('DO_NOT_PERSIST')):
            record=self.exercise()
        self.assertEqual(record['error'],'authentication_or_permission')
        self.assertEqual(record['error'],'authentication_or_permission')
        self.assertEqual(record['http_status'],401)
        self.assertTrue(record['diagnostic_capture_failed'])
        self.assertNotIn('DO_NOT_PERSIST',json.dumps(record))

    def test_runtime_provenance_with_dummy_environment_sources(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)/'.env';root.write_text('AZURE_OPENAI_API_KEY=synthetic-root\n')
            with patch.object(environment,'ENV_FILE',root),patch.object(environment,'_azure_credential_source','repository-root .env: AZURE_OPENAI_API_KEY'):
                self.assertEqual(environment.credential_provenance('synthetic-root'),{
                    'credential_source':'repository-root .env: AZURE_OPENAI_API_KEY','credential_matches_root_env':True})
                self.assertEqual(environment.credential_provenance('synthetic-override'),{
                    'credential_source':'process environment override: AZURE_OPENAI_API_KEY','credential_matches_root_env':False})
                with patch.object(environment,'_azure_credential_source','process environment: AZURE_OPENAI_API_KEY'):
                    self.assertEqual(environment.credential_provenance('synthetic-root')['credential_source'],'process environment: AZURE_OPENAI_API_KEY')

    def test_destination_excludes_query_and_userinfo(self):
        import httpx
        request=httpx.Request('POST','https://user:secret@offline.openai.azure.com/openai/v1/chat/completions?token=secret')
        self.assertEqual(diagnostics.destination(request,'https://offline.openai.azure.com/openai/v1'),{
            'scheme':'https','host':'offline.openai.azure.com','path':'/openai/v1/chat/completions'})
