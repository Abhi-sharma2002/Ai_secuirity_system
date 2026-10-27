"""No transport: verify the benchmark amendment cannot bypass cumulative limits."""
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

from app.evaluation import benchmark_scope as scope
from app.evaluation.simple_config import EvaluationError


class BenchmarkScopeTests(TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        for name, filename in [('SCOPE', 'scope.json'), ('JOURNAL', 'attempts.jsonl'), ('STOP', 'stopped')]:
            p = patch.object(scope, name, root / filename)
            p.start()
            self.addCleanup(p.stop)
        self.config = {'model': 'synthetic'}
        self.receipt = {'authorization': 'user-approved-pdf-alignment-continuation-20261027-v4', 'max_calls': 144,
                        'config': self.config, 'parent_allowance_id': 'synthetic',
                        'manifest_sha256': hashlib.sha256((scope.ROOT / 'backend/benchmark_v3/manifest.json').read_bytes()).hexdigest()}
        scope.SCOPE.write_text(json.dumps(self.receipt))
        self.approval = patch('app.llm.client.approval', return_value=SimpleNamespace(
            allowance_id='synthetic', provider='azure_openai', confirmed_free_promotional=True,
            paid_azure_test_authorized=False))
        self.approval.start()
        self.addCleanup(self.approval.stop)

    def test_shared_reservation_precedes_one_transport_call(self):
        with patch('app.llm.client.reserve', return_value=['reserved']) as reserve, patch(
                'app.llm.client.call', return_value=('{}', {})) as call:
            self.assertEqual(scope.invoke([], {}, 'generation', self.config), ('{}', {}))
            self.assertEqual(reserve.call_args.args, (1, 32000))
            call.assert_called_once_with([], {}, 'generation', 'reserved')
            self.assertEqual(len(scope.JOURNAL.read_text().splitlines()), 1)

    def test_exhausted_or_stopped_scope_never_reserves(self):
        scope.JOURNAL.write_text('{}\n' * 144)
        with patch('app.llm.client.reserve') as reserve:
            with self.assertRaises(EvaluationError): scope.invoke([], {}, 'generation', self.config)
            reserve.assert_not_called()
        scope.JOURNAL.write_text('')
        scope.stop()
        with patch('app.llm.client.reserve') as reserve:
            with self.assertRaises(EvaluationError): scope.invoke([], {}, 'generation', self.config)
            reserve.assert_not_called()

    def test_failure_preserves_reservation_and_permanent_stop(self):
        with patch('app.llm.client.reserve', return_value=['reserved']), patch(
                'app.llm.client.call', side_effect=RuntimeError('synthetic')):
            with self.assertRaises(EvaluationError): scope.invoke([], {}, 'generation', self.config)
        self.assertTrue(scope.STOP.exists())
        self.assertEqual(len(scope.JOURNAL.read_text().splitlines()), 1)

    def test_changed_configuration_never_reserves(self):
        with patch('app.llm.client.reserve') as reserve:
            with self.assertRaises(EvaluationError): scope.invoke([], {}, 'generation', {})
            reserve.assert_not_called()

    def test_only_approved_filter_refusals_may_advance(self):
        self.receipt['continue_content_filter_errors'] = True
        scope.SCOPE.write_text(json.dumps(self.receipt))
        self.assertTrue(scope.may_continue('provider_content_filter: refused'))
        self.assertFalse(scope.may_continue('provider_quota_error: stopped'))
        scope.stop()
        self.assertFalse(scope.may_continue('provider_content_filter: refused'))

    def test_filter_refusal_is_charged_once_without_retry_or_stopping_other_cases(self):
        from app.llm.client import ModelFailure
        self.receipt['continue_content_filter_errors'] = True
        scope.SCOPE.write_text(json.dumps(self.receipt))
        error = ModelFailure('invalid_request', {'provider_error_code':'content_filter'})
        with patch('app.llm.client.reserve', return_value=['reserved']), patch(
                'app.llm.client.call', side_effect=error) as call:
            with self.assertRaisesRegex(EvaluationError, 'provider_content_filter:'):
                scope.invoke([], {}, 'generation', self.config)
            self.assertEqual(call.call_count,1)
        self.assertFalse(scope.STOP.exists())
        self.assertEqual(len(scope.JOURNAL.read_text().splitlines()),1)
