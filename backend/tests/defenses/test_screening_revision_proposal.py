"""Offline candidate construction, using genuine saved evidence and blocked sockets.

The synthetic response is transport plumbing, never an evaluation result.
"""
import json
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import httpx
from langchain_core.messages import SystemMessage, HumanMessage
from app.llm import azure_openai
from app.llm.experiment_settings import identity_settings
from app.rag.assistant import SCREEN, Screening
from scripts.prepare_screening_revision import proposed_screening_payload

ROOT = Path(__file__).resolve().parents[3]
RUN = ROOT / 'backend/data/runtime/experiments/azure-development-08-12-stage-v1'


class ScreeningRevisionProposalTests(unittest.TestCase):
    def test_saved_screening_wire_changes_only_reasoning_effort(self):
        saved = json.loads((RUN / 'case-development-08-C-0.json').read_text())
        retrieval = json.loads((RUN / 'retrieval-development-08-0.json').read_text())['retrieval']
        prompt = [SystemMessage(content=SCREEN), HumanMessage(content=json.dumps({
            'question': saved['case']['query'], 'sources': retrieval['hits']}, ensure_ascii=True))]
        captured = []

        def blocked_transport(_transport, request):
            captured.append(json.loads(request.content))
            self.assertTrue(all(t == 30 for t in request.extensions['timeout'].values()))
            return httpx.Response(200, request=request, json={
                'choices': [{'message': {'content': ''}, 'finish_reason': 'length'}],
                'usage': {'prompt_tokens': 651, 'completion_tokens': 700, 'total_tokens': 1351}})

        config = SimpleNamespace(provider='azure_openai', model='gpt-5-mini-1',
            base_url='https://synthetic.invalid/openai/v1', api_key='SYNTHETIC-ONLY',
            request_timeout_seconds=30)
        with patch('socket.socket.connect', side_effect=AssertionError('Network prohibited')), \
             patch('socket.create_connection', side_effect=AssertionError('Network prohibited')), \
             patch.object(httpx.HTTPTransport, 'handle_request', new=blocked_transport):
            azure_openai.generate(prompt, Screening.model_json_schema(), config, lambda _: None, lambda _: None)
            azure_openai.generate(prompt, Screening.model_json_schema(), config, lambda _: None, lambda _: None,
                                  screening_reasoning_effort='minimal')
        self.assertEqual(len(captured), 2)
        old = captured[0]
        candidate = proposed_screening_payload(old)
        self.assertEqual(captured[1], candidate)
        self.assertNotIn('reasoning_effort', old)
        self.assertEqual(candidate.pop('reasoning_effort'), 'minimal')
        self.assertEqual(candidate, old)
        self.assertEqual(old['response_format']['json_schema']['schema'], Screening.model_json_schema())
        self.assertTrue(old['response_format']['json_schema']['strict'])
        self.assertEqual(json.loads(old['messages'][1]['content'])['sources'], saved['response']['candidate_evidence'])
        self.assertEqual(identity_settings()['configuration_version'], 'azure-gpt5mini-v2-temperature-not-sent')

    def test_rejects_answer_payload_and_other_setting_changes(self):
        payload = {'response_format': {'json_schema': {'name': 'Screening'}}, 'max_completion_tokens': 700}
        for changed in ({'max_completion_tokens': 701}, {'temperature': 1}, {'seed': 5},
                        {'reasoning_effort': 'low'}, {'response_format': {'json_schema': {'name': 'Answer'}}}):
            with self.subTest(change=changed), self.assertRaises(ValueError):
                proposed_screening_payload(payload | changed)

    def test_saved_failure_has_no_reasoning_count(self):
        response = json.loads((RUN / 'case-development-08-C-0.json').read_text())['response']
        call = response['calls'][0]
        self.assertEqual((call['http_status'], call['finish_reason'], call['usage']['output_tokens']), (200, 'length', 700))
        self.assertEqual(call['response_validation_error'], 'empty_content')
        for key in ('reasoning_tokens', 'completion_tokens_details', 'response_metadata'):
            self.assertIsNone(call.get(key))
