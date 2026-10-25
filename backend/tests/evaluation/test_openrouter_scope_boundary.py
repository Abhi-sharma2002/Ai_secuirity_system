import io
from contextlib import redirect_stdout
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from app.evaluation import experiment as exp
from app.llm.client import LiveBlocked


class ScopeBoundaryTests(unittest.TestCase):
    def test_interactive_scope_rejected_before_prepare_or_artifact_writes(self):
        with patch.object(exp, 'plan', return_value={'synthetic':True}), patch.object(exp, 'approval', return_value=SimpleNamespace(provider='openrouter')), patch.object(exp,'prepare',side_effect=AssertionError('Must not prepare experiment')), patch.object(exp,'load',side_effect=AssertionError('Must not load execution dataset')), redirect_stdout(io.StringIO()):
            with self.assertRaisesRegex(LiveBlocked, 'interactive allowance'):
                exp.run('synthetic-run', 'development', 'paired', 1, 5, True)
