"""Frozen synthetic wire parity; no actual provider or production persistence."""
import ast
import json
from pathlib import Path
import unittest

from backend.tests.llm import test_azure_openai as fixtures
from app.defenses import baseline, instruction_separation, screening
from app.rag import assistant

ROOT = Path(__file__).resolve().parents[3]


class RuntimeOrganizationTests(unittest.TestCase):
    def test_original_wire_and_schemas_allow_only_versioned_c_prompt_change(self):
        before = json.loads((ROOT/'docs/evidence/refactor-organization-v1/wire-before.json').read_text())
        revision = json.loads((ROOT/'docs/evidence/screening-question-source-contract-v2/before.json').read_text())
        with fixtures.AzureTests().session() as (observed, _, _):
            results = [assistant.respond('When are mentor check-ins?', mode, initial=fixtures.INITIAL) for mode in 'ABC']
        self.assertEqual([r['status'] for r in results], ['answered']*3)
        expected = before['payloads']
        self.assertEqual(expected[2]['messages'][0]['content'], revision['screen'])
        expected[2]['messages'][0]['content'] = screening.SCREEN
        self.assertEqual([json.loads(r.content) for r in observed], expected)
        self.assertEqual(screening.PROMPT_VERSION, 'screening-question-source-contract-v2')
        self.assertNotEqual(assistant.PROMPT_HASH, before['prompt_hash'])
        self.assertEqual(assistant.Answer.model_json_schema(), before['schemas']['answer'])
        self.assertEqual(assistant.Screening.model_json_schema(), before['schemas']['screening'])
        self.assertEqual(assistant.messages('A', 'q', []), baseline.messages('q', []))
        self.assertEqual(assistant.messages('B', 'q', []), instruction_separation.messages('q', []))
        self.assertIs(assistant.Screening, screening.Screening)

    def test_active_runtime_has_no_legacy_provider_or_defense_dependency(self):
        files = ['api/runtime.py','rag/assistant.py','rag/retrieval.py','rag/indexer.py',
                 'defenses/baseline.py','defenses/instruction_separation.py','defenses/screening.py',
                 'llm/client.py','llm/azure_openai.py','storage/registry.py']
        for name in files:
            with self.subTest(file=name):
                tree = ast.parse((ROOT/'backend/app'/name).read_text())
                modules = [n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) and n.module]
                self.assertFalse(any(n.startswith(('legacy_llm','app.legacy')) for n in modules))
        tree = ast.parse((ROOT/'backend/app/storage/registry.py').read_text())
        modules = [n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) and n.module]
        self.assertFalse(any(n.startswith(('app.api','frontend')) for n in modules))
