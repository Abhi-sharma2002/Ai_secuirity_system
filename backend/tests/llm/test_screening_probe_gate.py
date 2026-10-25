"""Synthetic transport and isolated ledgers; never activates a real allowance."""
import json
import unittest
from types import SimpleNamespace
from unittest.mock import patch
import httpx
from app.llm import azure_openai
from app.llm import client as live
from app.rag import assistant
from backend.tests.llm import test_azure_openai as fixtures


class ScreeningProbeGateTests(unittest.TestCase):
    def test_explicit_gate_one_call_and_no_second_reservation(self):
        with fixtures.AzureTests().session(capacity=1) as (requests, a, path):
            a = a.model_copy(update={'allowance_id': 'azure-development08-screening-minimal-probe-v1'})
            path.write_text(a.model_dump_json())
            meta = {'diagnostic_id': a.allowance_id, 'case_id': 'development-08', 'mode': 'C_screening_only'}
            rid = live.reserve(1, 32000, metadata=meta)[0]
            raw, trace = live.call([{'role': 'developer', 'content': assistant.SCREEN},
                {'role': 'user', 'content': '{"question":"Synthetic?","sources":[]}'}],
                assistant.Screening.model_json_schema(), 'screening', rid, screening_reasoning_effort='minimal')
            assistant.Screening.model_validate_json(raw)
            self.assertEqual(len(requests), 1)
            self.assertEqual(json.loads(requests[0].content)['reasoning_effort'], 'minimal')
            self.assertEqual(trace['settings']['max_output_tokens'], 700)
            self.assertEqual(trace['settings']['reasoning_effort'], 'minimal')
            self.assertIsNone(trace['reasoning_tokens'])
            self.assertEqual(json.loads(trace['response_content'])['question_flagged'], False)
            with self.assertRaises(live.LiveBlocked):
                live.reserve(1, 32000, metadata=meta)

    def test_wrong_receipt_cannot_use_revision(self):
        with fixtures.AzureTests().session(capacity=1) as (requests, a, path):
            rid = live.reserve(1, 32000, metadata={'diagnostic_id': a.allowance_id, 'case_id': 'development-08'})[0]
            with self.assertRaises(live.LiveBlocked):
                live.call([], assistant.Screening.model_json_schema(), 'screening', rid, screening_reasoning_effort='minimal')
            self.assertEqual(len(requests), 0)

    def test_adapter_retains_only_safe_numeric_reasoning_detail(self):
        config = SimpleNamespace(provider='azure_openai', model='synthetic', request_timeout_seconds=30,
                                 base_url='https://synthetic.invalid/openai/v1', api_key='SYNTHETIC-ONLY')
        for value, expected in ((0, 0), (88, 88), (True, None), (-1, None), ('unsafe arbitrary text', None)):
            def transport(_transport, request):
                return httpx.Response(200, request=request, json={'choices': [{'message': {'content': '{}'}, 'finish_reason': 'stop'}],
                    'usage': {'prompt_tokens': 1, 'completion_tokens': 100, 'total_tokens': 101,
                              'completion_tokens_details': {'reasoning_tokens': value, 'untrusted': 'must not persist'}}})
            with self.subTest(value=value), patch('socket.socket.connect', side_effect=AssertionError('No network')), \
                 patch.object(httpx.HTTPTransport, 'handle_request', new=transport):
                result = azure_openai.generate([], assistant.Screening.model_json_schema(), config, lambda _: None, lambda _: None,
                                               screening_reasoning_effort='minimal')
            self.assertEqual(result.response_metadata.get('reasoning_tokens'), expected)
            self.assertNotIn('untrusted', result.response_metadata)
