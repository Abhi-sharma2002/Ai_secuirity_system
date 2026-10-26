"""Runner mechanics only: synthetic answers in disposable directories, no efficacy data."""
from contextlib import ExitStack
from copy import deepcopy
import csv
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import run_eval as run
from app.evaluation import simple_runner as assistant
from app.evaluation.simple_config import EvaluationError


class RunEvaluationTests(unittest.TestCase):
    def setUp(self):
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.directory = Path(self.stack.enter_context(tempfile.TemporaryDirectory()))
        self.output = self.directory / 'synthetic-only'
        self.data, self.config, self.manifest_sha = run._inputs()
        self.identity = {'generation': 'synthetic-index'}
        self.stack.enter_context(patch.dict(os.environ, {'EVAL_MODE': '1'}))
        self.stack.enter_context(patch('socket.socket.connect', side_effect=AssertionError('Network forbidden')))
        self.stack.enter_context(patch.object(assistant, 'STORE', self.directory / 'index'))
        self.stack.enter_context(patch.object(assistant, '_identity', return_value=self.identity))
        self.stack.enter_context(patch.object(run, 'OUTPUT', self.output))
        self.retrieve = self.stack.enter_context(patch.object(assistant, '_retrieve', side_effect=self.hits))
        self.ask = self.stack.enter_context(patch.object(assistant, 'ask', side_effect=self.answer))
        self.addCleanup(assistant._CACHE.clear)

    def hits(self, question, doc_ids, config, identity):
        return [{'id': doc_ids[0] + '_synthetic', 'document_id': doc_ids[0],
                 'text': 'Synthetic fixture text.', 'filename': 'synthetic.txt'}]

    def answer(self, mode, question, doc_ids):
        hits = deepcopy(assistant._CACHE['hits'])
        return {**run._error_result('', hits), 'answer': 'Synthetic mechanics test answer.',
                'kept_chunk_ids': [h['id'] for h in hits] if mode == 'C' else [], 'latency_s': 0.01}

    def execute(self, **kwargs):
        return run._run(self.data, self.config, self.manifest_sha,
                        output=self.output, origin='synthetic_test', **kwargs)

    def rows(self):
        with (self.output / 'records.csv').open(newline='') as handle:
            reader = csv.DictReader(handle)
            self.assertEqual(reader.fieldnames, run.COLUMNS)
            return list(reader)

    def test_plan_counts_and_cli_never_dispatch(self):
        plan = run._plan(self.data, 3)
        self.assertEqual((plan['selected_records'], plan['selected_calls_upper_bound']), (9, 12))
        self.assertEqual((plan['full_records'], plan['full_plus_smokes_calls_upper_bound']), (141, 193))
        self.assertEqual(plan['automatic_retries'], 0)
        self.assertIsNone(plan['published_default_daily_requests'])
        self.assertIsNone(plan['published_requests_per_minute'])
        self.assertIn('learn.microsoft.com', plan['limits_reference'])
        self.assertFalse(plan['live_execution_enabled'])
        with patch('builtins.print'):
            self.assertEqual(run.main(['--plan', '--limit', '3']), 0)
        with self.assertRaises(SystemExit) as stopped:
            run.main(['--limit', '3'])
        self.assertEqual(stopped.exception.code, 1)
        self.assertFalse(self.output.exists())
        self.ask.assert_not_called()
        self.retrieve.assert_not_called()

    def test_nine_rows_then_resume_to_full_without_duplicates(self):
        self.assertEqual(self.execute(limit=3)['added'], 9)
        first = self.rows()
        self.assertEqual(len(first), 9)
        self.assertEqual(self.retrieve.call_count, 3)
        self.assertEqual(self.execute(limit=3, resume=True)['added'], 0)
        result = self.execute(resume=True)
        self.assertEqual(result['records'], 141)
        self.assertEqual(len(self.rows()), 141)
        self.assertEqual(len({(r['case_id'], r['mode']) for r in self.rows()}), 141)
        self.assertEqual(self.rows()[:9], first)
        self.assertEqual(self.retrieve.call_count, 47)
        self.assertEqual(self.ask.call_count, 141)
        self.assertTrue(all(r['answer'] or r['error'] for r in self.rows()))
        metadata = json.loads((self.output / 'run_metadata.json').read_text())
        self.assertEqual(metadata['origin'], 'synthetic_test')

    def test_rows_are_flushed_before_next_ask(self):
        def answer(*args):
            self.assertEqual(len(self.rows()), self.ask.call_count - 1)
            return self.answer(*args)
        self.ask.side_effect = answer
        self.execute(limit=3)
        self.assertEqual(len(self.rows()), 9)

    def test_errors_filters_and_empty_answers_are_not_blocks_or_retried(self):
        failures = iter(['HTTP 429', 'Provider content filter', 'Timeout'])
        def answer(*args):
            return {**run._error_result(next(failures)), 'blocked': True}
        self.ask.side_effect = answer
        self.execute(limit=1)
        self.assertEqual(self.ask.call_count, 3)
        for row in self.rows():
            self.assertTrue(row['error'])
            self.assertEqual(row['blocked'], 'false')
            for key in ('attack_succeeded', 'task_passed', 'false_positive', 'answer_chunk_removed', 'citation_correct'):
                self.assertEqual(row[key], '')
        self.execute(limit=1, resume=True)
        self.assertEqual(self.ask.call_count, 3)

    def test_empty_answer_gets_error(self):
        self.ask.side_effect = None
        self.ask.return_value = run._error_result('')
        self.execute(limit=1)
        self.assertTrue(all('empty answer' in row['error'] for row in self.rows()))

    def test_interrupted_row_is_not_replayed_and_saved_retrieval_is_reused(self):
        def interrupt(mode, *args):
            if mode == 'B':
                raise KeyboardInterrupt
            return self.answer(mode, *args)
        self.ask.side_effect = interrupt
        with self.assertRaises(KeyboardInterrupt):
            self.execute(limit=1)
        self.assertEqual(len(self.rows()), 1)
        self.ask.reset_mock(side_effect=True)
        self.ask.side_effect = self.answer
        self.execute(limit=1, resume=True)
        self.retrieve.assert_called_once()
        self.assertEqual([c.args[0] for c in self.ask.call_args_list], ['C'])
        rows = self.rows()
        self.assertEqual([r['mode'] for r in rows], list('ABC'))
        self.assertIn('Interrupted row', rows[1]['error'])
        self.assertEqual(rows[0]['retrieved_chunk_ids'], rows[2]['retrieved_chunk_ids'])

    def test_retrieval_failure_persisted_for_all_modes_without_model_call(self):
        self.retrieve.side_effect = EvaluationError('Local index unavailable')
        self.execute(limit=1)
        self.ask.assert_not_called()
        self.retrieve.assert_called_once()
        self.assertEqual({r['error'] for r in self.rows()}, {'Local index unavailable'})

    def test_resume_rejects_changed_config_index_or_code_without_overwrite(self):
        self.execute(limit=1)
        original = (self.output / 'records.csv').read_bytes()
        for target, value in [('config', {**self.config, 'max_tokens': 701}),
                              ('index', {'generation': 'different'}), ('code', {'implementation_sha256': 'changed'})]:
            with self.subTest(target=target), ExitStack() as stack:
                if target == 'config':
                    stack.enter_context(patch.object(self, 'config', value))
                elif target == 'index':
                    stack.enter_context(patch.object(assistant, '_identity', return_value=value))
                else:
                    base = run._metadata(self.config, self.manifest_sha, self.identity, 'synthetic_test')
                    stack.enter_context(patch.object(run, '_metadata', return_value={**base, **value}))
                with self.assertRaisesRegex(EvaluationError, 'identity changed'):
                    self.execute(limit=2, resume=True)
                self.assertEqual((self.output / 'records.csv').read_bytes(), original)

    def test_existing_artifacts_are_not_overwritten(self):
        self.execute(limit=1)
        original = (self.output / 'records.csv').read_bytes()
        with self.assertRaisesRegex(EvaluationError, 'require --resume'):
            self.execute(limit=1)
        self.assertEqual((self.output / 'records.csv').read_bytes(), original)

    def test_prepare_only_cannot_replace_a_resumed_or_recorded_index(self):
        with patch.object(run, 'prepare_store') as prepare:
            with self.assertRaises(SystemExit):
                run.main(['--prepare-only', '--resume'])
            self.execute(limit=1)
            with self.assertRaises(SystemExit):
                run.main(['--prepare-only'])
            prepare.assert_not_called()

    def test_resume_rejects_duplicate_or_different_header_rows(self):
        self.execute(limit=1)
        path = self.output / 'records.csv'
        original = path.read_text()
        duplicate = original + original.splitlines(keepends=True)[1]
        for corrupted in (duplicate, original.replace('case_id,', 'wrong_header,', 1)):
            with self.subTest(header=corrupted.startswith('wrong_header')):
                path.write_text(corrupted)
                with self.assertRaises(EvaluationError):
                    self.execute(limit=1, resume=True)
                self.assertEqual(path.read_text(), corrupted)

    def test_runner_requires_explicit_evaluation_mode(self):
        with patch.dict(os.environ, {'EVAL_MODE': '0'}), self.assertRaisesRegex(EvaluationError, 'EVAL_MODE=1'):
            self.execute(limit=1)
        self.ask.assert_not_called()
        self.assertFalse(self.output.exists())

    def test_corrupt_retrieval_rejected_on_partial_resume(self):
        self.ask.side_effect = KeyboardInterrupt
        with self.assertRaises(KeyboardInterrupt):
            self.execute(limit=1)
        evidence = next((self.output / 'retrieval').glob('*.json'))
        stored = json.loads(evidence.read_text())
        stored['hits'][0]['text'] = 'Changed evidence'
        evidence.write_text(json.dumps(stored))
        with self.assertRaisesRegex(EvaluationError, 'retrieval changed'):
            self.execute(limit=1, resume=True)

    def test_private_exception_is_redacted(self):
        self.ask.side_effect = RuntimeError('Authorization: Bearer SYNTHETIC-SECRET')
        self.execute(limit=1)
        self.assertNotIn('SYNTHETIC-SECRET', (self.output / 'records.csv').read_text())
        self.assertTrue(all(r['error'] for r in self.rows()))


class RequestPacingTests(unittest.TestCase):
    def test_each_call_observes_start_rate_and_completion_gap(self):
        clock = [0.0]
        def sleep(seconds):
            clock[0] += seconds
        def model(*args):
            clock[0] += 4.0
            return 'synthetic', {}
        with patch.dict(assistant._LAST_CALL, started=None, finished=None), \
             patch.object(assistant, 'perf_counter', side_effect=lambda: clock[0]), \
             patch.object(assistant, 'sleep', side_effect=sleep) as wait, \
             patch.object(assistant, '_model_call', side_effect=model):
            assistant._invoke_model([], {}, 'screening', {})
            assistant._invoke_model([], {}, 'generation', {})
            wait.assert_called_once_with(1.0)
            self.assertEqual(assistant._LAST_CALL['started'], 5.0)
        clock[0] = 0
        with patch.dict(assistant._LAST_CALL, started=0.0, finished=0.5), \
             patch.object(assistant, 'perf_counter', side_effect=lambda: clock[0]), \
             patch.object(assistant, 'sleep', side_effect=sleep) as wait:
            assistant._pace_call()
            wait.assert_called_once_with(3.1)


if __name__ == '__main__':
    unittest.main()
