"""Baseline one-case execution/CLI tests. No live providers or network connections."""
import io
import json
import os
import socket
import stat
import tempfile
import unittest
from contextlib import redirect_stdout, redirect_stderr
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from app.legacy.defenses.base import PromptPreparationError
from app.legacy.defenses.baseline_runner import BaselineRunner, save_execution
from app.evaluation.evidence_builder import build_evidence, load_verified_sources
from app.evaluation.test_case_loader import load_test_cases
from legacy_llm.client import LLMClient, ProviderError, ProviderResponse
from legacy_llm.fake import FakeAdapter
from legacy_llm.models import LLMConfig
from legacy_llm.usage import Pricing, TokenUsage
from decimal import Decimal
from scripts.run_baseline import main


class BaselineRunnerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases = load_test_cases()
        cls.sources = load_verified_sources()

    def setUp(self):
        guard = patch.object(socket.socket, 'connect', side_effect=AssertionError('Unexpected network'))
        guard.start()
        self.addCleanup(guard.stop)
        self.case = self.cases[0]
        self.evidence = build_evidence(self.case, self.sources)

    def runner(self, events=None, pricing=None):
        adapter = FakeAdapter(events if events is not None else [ProviderResponse('answer [D001]')])
        client = LLMClient(LLMConfig(max_retries=0), adapter, pricing=pricing)
        return BaselineRunner(client, self.sources), adapter

    def test_success_capture_question_answer_usage_and_settings(self):
        pricing = Pricing('fake', 'fake-model', 'unit-test-v1', Decimal('2'), Decimal('4'))
        runner, adapter = self.runner([ProviderResponse('answer [D001]', TokenUsage(20, 5))], pricing)
        execution = runner.run(self.case, temperature=0.0, max_output_tokens=100)
        metadata = execution.safe_metadata()
        self.assertEqual(execution.content.question, self.case['question'])
        self.assertEqual(execution.content.answer, 'answer [D001]')
        self.assertEqual(metadata['test_id'], 'E001')
        self.assertEqual(metadata['configuration_id'], 'A')
        self.assertEqual(metadata['evidence_fingerprint'], self.evidence.fingerprint)
        self.assertEqual(metadata['generation_settings'], {'temperature': 0.0, 'max_output_tokens': 100})
        self.assertEqual(metadata['total_tokens'], 25)
        self.assertEqual(metadata['estimated_cost_usd'], '0.00006')
        self.assertEqual(metadata['attempt_count'], 1)
        self.assertEqual(metadata['latency_ms'], execution.usage.latency_ms)
        self.assertGreaterEqual(metadata['latency_ms'], 0)
        self.assertEqual(metadata['status'], 'succeeded')
        self.assertTrue(metadata['simulated'])
        self.assertEqual(metadata['execution_mode'], 'simulated')
        self.assertIs(adapter.calls[0][0], execution.prepared.request)
        self.assertNotIn('task_success', metadata)
        self.assertNotIn('attack_success', metadata)
        self.assertNotIn('answer [D001]', json.dumps(metadata))

    def test_received_evidence_is_reused_without_loading_again(self):
        runner, adapter = self.runner()
        with patch('app.legacy.defenses.baseline_runner.build_evidence', side_effect=AssertionError('Must reuse')):
            execution = runner.run(self.case, evidence=self.evidence)
        self.assertTrue(adapter.calls[0][0].messages[1].content.endswith(self.evidence.evidence_text))
        self.assertEqual(execution.usage.evidence_fingerprint, self.evidence.fingerprint)

    def test_mismatched_case_package_rejected_before_call(self):
        runner, adapter = self.runner()
        for evidence in [replace(self.evidence, test_id='E002'),
                         replace(self.evidence, question='different'),
                         replace(self.evidence, document_ids=('D002',))]:
            with self.assertRaises(PromptPreparationError):
                runner.run(self.case, evidence=evidence)
        with self.assertRaises(PromptPreparationError):
            runner.run(dict(self.case, supporting_document_sha256='0'*64), evidence=self.evidence)
        self.assertEqual(adapter.calls, [])

    def test_invalid_boundary_case_is_rejected(self):
        runner, adapter = self.runner()
        for case in [None, {}, dict(self.case, evidence_mode='retrieved'),
                     dict(self.case, document_ids=['../../bad']), dict(self.case, question='')]:
            with self.assertRaises(PromptPreparationError):
                runner.run(case)
        self.assertEqual(adapter.calls, [])

    def test_citations_are_candidates_not_validated_support(self):
        runner, _ = self.runner([ProviderResponse('Claim [D001]; another D999. XD001 D001_suffix D001.')])
        execution = runner.run(self.case)
        mentions = execution.content.citation_candidates
        self.assertEqual([mention.document_id for mention in mentions], ['D001', 'D999', 'D001'])
        self.assertEqual([mention.in_supplied_evidence for mention in mentions], [True, False, True])
        for candidate in mentions:
            self.assertEqual(candidate.validation_status, 'not_validated')
            self.assertEqual(execution.content.answer[candidate.start_char:candidate.end_char], candidate.document_id)

    def test_failed_execution_preserved_without_fabricated_answer(self):
        runner, _ = self.runner([ProviderError('authentication')])
        execution = runner.run(self.case)
        self.assertEqual(execution.status, 'failed')
        self.assertIsNone(execution.content.answer)
        self.assertEqual(execution.content.citation_candidates, ())
        self.assertEqual(execution.safe_metadata()['error_category'], 'authentication')
        self.assertEqual(execution.usage.attempt_count, 1)
        self.assertEqual(runner.client.tracker.snapshot(), (execution.usage,))

    def test_missing_usage_and_price_remain_unknown(self):
        runner, _ = self.runner()
        metadata = runner.run(self.case).safe_metadata()
        for key in ['input_tokens', 'output_tokens', 'total_tokens', 'estimated_cost_usd']:
            self.assertIsNone(metadata[key])
        self.assertIsNone(metadata['llm']['total_estimated_cost_usd'])

    def test_fake_subclass_cannot_be_labeled_real_by_provider_name(self):
        class RenamedFake(FakeAdapter):
            provider = 'renamed'
        client = LLMClient(LLMConfig(provider='renamed', model='model'), RenamedFake())
        self.assertEqual(BaselineRunner(client, self.sources).run(self.case).execution_mode, 'simulated')

    def test_private_recording_separates_text_and_never_overwrites(self):
        runner, _ = self.runner()
        execution = runner.run(self.case)
        with tempfile.TemporaryDirectory() as directory:
            first = save_execution(execution, directory)
            second = save_execution(execution, directory)
            self.assertNotEqual(first, second)
            for path in (first, second):
                self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o700)
                metadata = json.loads((path / 'metadata.json').read_text())
                content = json.loads((path / 'untrusted_content.json').read_text())
                self.assertEqual(content['question'], self.case['question'])
                self.assertEqual(content['answer'], execution.content.answer)
                self.assertNotIn('answer', metadata)
                self.assertNotIn('question', metadata)
                self.assertEqual(content['citation_candidates'][0]['validation_status'], 'not_validated')
                self.assertTrue(metadata['simulated'])
                for file in path.iterdir():
                    self.assertEqual(stat.S_IMODE(file.stat().st_mode), 0o600)

    def test_partial_recording_failure_is_cleaned(self):
        runner, _ = self.runner()
        execution = runner.run(self.case)
        with tempfile.TemporaryDirectory() as directory:
            with patch('app.legacy.defenses.baseline_runner.json.dump', side_effect=OSError('disk failure')):
                with self.assertRaises(OSError):
                    save_execution(execution, directory)
            self.assertEqual(list(Path(directory).iterdir()), [])

    def test_recording_rejects_symlink_directory(self):
        runner, _ = self.runner()
        execution = runner.run(self.case)
        with tempfile.TemporaryDirectory() as directory:
            link = Path(directory) / 'link'
            link.symlink_to(directory, target_is_directory=True)
            with self.assertRaises(ValueError):
                save_execution(execution, link)

    def cli(self, args, env=None):
        output, error = io.StringIO(), io.StringIO()
        with patch.dict('os.environ', env or {}, clear=True), redirect_stdout(output), redirect_stderr(error):
            code = main(args)
        return code, output.getvalue(), error.getvalue()

    def test_cli_fake_default_ignores_live_environment_and_hides_content(self):
        with tempfile.TemporaryDirectory() as directory:
            code, output, _ = self.cli(['--test-id', 'E001', '--output-dir', directory],
                                       {'LLM_PROVIDER': 'live', 'LLM_MODEL': 'live-model', 'LLM_API_KEY': 'secret'})
            self.assertEqual(code, 0)
            self.assertIn('SIMULATED', output)
            self.assertNotIn('secret', output)
            self.assertNotIn(self.case['question'], output)
            files = list(Path(directory).glob('*/metadata.json'))
            self.assertEqual(len(files), 1)
            self.assertEqual(json.loads(files[0].read_text())['execution_mode'], 'simulated')

    def test_cli_unknown_case_and_live_without_approval_do_not_record(self):
        with tempfile.TemporaryDirectory() as directory:
            for args, env in [(['--test-id', 'E999'], {}),
                              (['--test-id', 'E001', '--allow-live'], {}),
                              (['--test-id', 'E001', '--allow-live'],
                               {'LLM_PROVIDER': 'live', 'LLM_MODEL': 'model', 'LLM_API_KEY': 'secret'})]:
                code, output, error = self.cli(args + ['--output-dir', directory], env)
                self.assertNotEqual(code, 0)
                self.assertNotIn('secret', output + error)
                self.assertEqual(list(Path(directory).iterdir()), [])

    def test_cli_provider_failure_records_failure_and_returns_nonzero(self):
        runner, _ = self.runner([ProviderError('authentication')])
        with tempfile.TemporaryDirectory() as directory:
            with patch('scripts.run_baseline.LLMClient', return_value=runner.client):
                code, output, _ = self.cli(['--test-id', 'E001', '--output-dir', directory])
            self.assertEqual(code, 1)
            self.assertIn('"status": "failed"', output)
            content_file = next(Path(directory).glob('*/untrusted_content.json'))
            self.assertIsNone(json.loads(content_file.read_text())['answer'])

    def test_untrusted_output_cannot_control_paths_or_execute(self):
        runner, _ = self.runner([ProviderResponse('../../overwrite.txt; os.system("echo unsafe")')])
        with patch('os.system') as system:
            execution = runner.run(self.case)
            with tempfile.TemporaryDirectory() as directory:
                saved = save_execution(execution, directory)
                self.assertEqual(saved.parent, Path(directory))
                self.assertEqual({file.name for file in saved.iterdir()}, {'metadata.json', 'untrusted_content.json'})
        system.assert_not_called()
