"""Validate the Azure screening wire contract without network calls."""
import json
import os
from unittest import TestCase
from unittest.mock import patch
from app.evaluation import simple_runner as runner


class BenchmarkWireTests(TestCase):
    def test_clear_screening_has_explicit_empty_reason_instructions(self):
        response = {'question_flagged': False, 'flagged_source_ids': [], 'reason_codes': ['none'],
                    'question_reason': '', 'source_reasons': []}
        with patch.dict(os.environ, {'EVAL_MODE': '1', 'LIVE_EVALUATION_ENABLED': 'true'}), patch(
                'app.evaluation.benchmark_scope.invoke', return_value=(json.dumps(response), {})) as invoke:
            raw, _ = runner._model_call([{'role': 'system', 'content': 'screen'}],
                                       runner._ScreeningWithReasons.model_json_schema(), 'screening', {})
        self.assertEqual(json.loads(raw)['source_reasons'], {})
        messages, schema, _, _ = invoke.call_args.args
        self.assertIn('question_reason must be the empty string', messages[-1]['content'])
        self.assertIn('never repeat a reason code', messages[-1]['content'])
        self.assertIn('none must appear alone', messages[-1]['content'])
        self.assertIn('ONLY for flagged_source_ids', schema['properties']['source_reasons']['description'])

    def test_duplicate_reasons_fail_without_retry(self):
        response = {'question_flagged': False, 'flagged_source_ids': ['one'], 'reason_codes': ['instruction_redirection'],
                    'question_reason': '', 'source_reasons': [{'source_id': 'one', 'reason': 'a'}, {'source_id': 'one', 'reason': 'b'}]}
        with patch.dict(os.environ, {'EVAL_MODE': '1', 'LIVE_EVALUATION_ENABLED': 'true'}), patch(
                'app.evaluation.benchmark_scope.invoke', return_value=(json.dumps(response), {})) as invoke:
            with self.assertRaises(runner.EvaluationError):
                runner._model_call([], runner._ScreeningWithReasons.model_json_schema(), 'screening', {})
            self.assertEqual(invoke.call_count, 1)
