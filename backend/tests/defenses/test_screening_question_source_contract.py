"""Question/source distinction, blocked transport, original saved evidence unchanged."""
import json
from pathlib import Path
import unittest

from backend.tests.defenses import test_phase8_screening as fixtures
from app.defenses import screening
from app.rag import assistant

ROOT = Path(__file__).resolve().parents[3]


class QuestionSourceContractTests(unittest.TestCase):
    def test_saved_invalid_id_still_fails_closed_with_exact_frozen_inputs(self):
        diagnostic = ROOT/'backend/data/runtime/diagnostics/azure-development08-screening-minimal-probe-v1'
        run = ROOT/'backend/data/runtime/experiments/azure-development-08-12-stage-v1'
        saved = json.loads((diagnostic/'response.json').read_text())
        case = json.loads((run/'case-development-08-C-0.json').read_text())
        frozen = json.loads((run/'retrieval-development-08-0.json').read_text())['retrieval']
        invalid = saved['call']['response_content']
        self.assertEqual(json.loads(invalid)['flagged_source_ids'], ['user_message'])
        self.assertNotIn('user_message', {h['id'] for h in frozen['hits']})
        with fixtures.ScreeningTests().session(invalid) as (_, observed, _):
            result = assistant.respond(case['case']['query'], 'C', initial=frozen)
        self.assertEqual(result['status'], 'screening_error')
        self.assertEqual(result['error'], 'invalid_screening_schema_or_ids')
        self.assertIsNone(result['screening'])
        self.assertEqual(len(observed), 1, 'No answering or repair call')
        self.assertEqual(json.loads(observed[0]['body']['messages'][1]['content']),
                         {'question': case['case']['query'], 'sources': frozen['hits']})
        self.assertEqual(observed[0]['body']['messages'][0]['content'], screening.SCREEN)
        self.assertEqual(result['candidate_evidence'], frozen['hits'])
        self.assertEqual(result['screening_prompt_version'], screening.PROMPT_VERSION)

    def test_question_only_flags_block_without_any_document_id(self):
        decision = {'question_flagged': True, 'flagged_source_ids': [],
                    'reason_codes': ['instruction_redirection']}
        with fixtures.ScreeningTests().session(decision) as (initial, observed, _):
            result = assistant.respond('Synthetic question-only injection', 'C', initial=initial)
        self.assertEqual(result['status'], 'policy_blocked')
        self.assertEqual(result['screening'], decision)
        self.assertEqual(len(observed), 1)
        self.assertEqual(result['candidate_evidence'], initial['hits'])

    def test_question_and_document_flags_remain_independent(self):
        decision = {'question_flagged': True, 'flagged_source_ids': ['s1'],
                    'reason_codes': ['instruction_redirection']}
        with fixtures.ScreeningTests().session(decision) as (initial, observed, _):
            result = assistant.respond('Synthetic mixed injection', 'C', initial=initial)
        self.assertEqual(result['status'], 'policy_blocked')
        self.assertEqual(result['screening'], decision)
        self.assertEqual(len(observed), 1)

    def test_schema_is_unchanged_and_question_is_not_a_source(self):
        old = json.loads((ROOT/'docs/evidence/screening-question-source-contract-v2/before.json').read_text())
        self.assertEqual(screening.Screening.model_json_schema(), old['schema'])
        self.assertIn('the question is not a source and has no source ID', screening.SCREEN)
        self.assertIn('an empty list', screening.SCREEN)
