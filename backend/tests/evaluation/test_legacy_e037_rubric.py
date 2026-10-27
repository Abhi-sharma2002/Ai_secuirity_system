"""Offline rubric binding checks, not real model responses or human grades."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from app.legacy.defenses.baseline_runner import BaselineRunner, save_execution
from app.legacy import legacy_rubrics
from app.evaluation.evidence_builder import load_verified_sources
from legacy_llm.client import LLMClient, ProviderResponse
from legacy_llm.fake import FakeAdapter
from legacy_llm.models import LLMConfig


class LegacyE037RubricTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.path = legacy_rubrics.ROOT/'backend/data/test_cases/test_cases_verified.json'
        cls.original = cls.path.read_bytes()
        cls.case = next(c for c in json.loads(cls.original) if c['test_id']=='E037')
        cls.sources = load_verified_sources()

    def setUp(self):
        self.guard = patch('socket.socket.connect',side_effect=AssertionError('Network forbidden'))
        self.guard.start();self.addCleanup(self.guard.stop)

    def test_exact_approved_text_and_original_preserved(self):
        bound = legacy_rubrics.for_case(self.case)
        proposal = legacy_rubrics.RUBRIC.parent/'proposal.before.md'
        exact = ' '.join(line[2:] for line in proposal.read_text().splitlines() if line.startswith('> '))
        self.assertEqual(bound['version'],'legacy-e037-task-v2')
        self.assertEqual(bound['criteria']['task_success_definition'],exact)
        self.assertEqual(bound['criteria']['original_task_success_definition'],self.case['task_success_definition'])
        self.assertEqual(bound['criteria']['attack_success_definition'],'not_applicable')
        self.assertEqual(self.path.read_bytes(),self.original)
        archived = json.loads((legacy_rubrics.RUBRIC.parent/'E037.original.json').read_text())
        self.assertEqual(archived,self.case)

    def test_future_execution_saves_version_hash_and_criteria_without_grades(self):
        adapter = FakeAdapter([ProviderResponse('SYNTHETIC response; rubric-binding fixture only')])
        runner = BaselineRunner(LLMClient(LLMConfig(max_retries=0),adapter),self.sources)
        execution = runner.run(self.case)
        metadata = execution.safe_metadata()
        self.assertEqual(metadata['schema_version'],2)
        self.assertEqual(metadata['evaluation_rubric'],legacy_rubrics.for_case(self.case))
        self.assertTrue(metadata['simulated'])
        self.assertNotIn('task_success',metadata)
        self.assertNotIn('attack_success',metadata)
        # Evaluator rules must not enter the generated prompt.
        text = '\n'.join(m.content for m in adapter.calls[0][0].messages)
        self.assertNotIn(metadata['evaluation_rubric']['criteria']['task_success_definition'],text)
        with tempfile.TemporaryDirectory() as tmp:
            folder = save_execution(execution,tmp)
            saved = json.loads((folder/'metadata.json').read_text())
            self.assertEqual(saved['evaluation_rubric'],metadata['evaluation_rubric'])

    def test_changed_case_refused_before_generation(self):
        adapter = FakeAdapter([ProviderResponse('SYNTHETIC unused')])
        runner = BaselineRunner(LLMClient(LLMConfig(max_retries=0),adapter),self.sources)
        altered = dict(self.case,task_success_definition='Unapproved replacement')
        with self.assertRaisesRegex(ValueError,'new version/review'):
            runner.run(altered)
        self.assertEqual(adapter.calls,[])

    def test_other_legacy_cases_keep_original_metadata_schema(self):
        case = next(c for c in json.loads(self.original) if c['test_id']=='E038')
        adapter = FakeAdapter([ProviderResponse('SYNTHETIC response')])
        execution = BaselineRunner(LLMClient(LLMConfig(max_retries=0),adapter),self.sources).run(case)
        self.assertEqual(execution.safe_metadata()['schema_version'],1)
        self.assertNotIn('evaluation_rubric',execution.safe_metadata())

    def test_hash_distinguishes_modified_criteria_without_upgrading_old_metadata(self):
        original = legacy_rubrics.for_case(self.case)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'rubric.json'
            changed = deepcopy(original['criteria'])
            changed['task_success_definition'] += ' SYNTHETIC unapproved drift'
            path.write_text(json.dumps(changed))
            with patch.object(legacy_rubrics,'RUBRIC',path):
                alternate = legacy_rubrics.for_case(self.case)
        self.assertNotEqual(original['sha256'],alternate['sha256'])
        self.assertNotIn('SYNTHETIC unapproved drift',original['criteria']['task_success_definition'])
        # An old saved metadata object is never passed through for_case or rewritten.
        historical = {'schema_version':1,'test_id':'E037','task_success':True}
        before = deepcopy(historical)
        legacy_rubrics.for_case(self.case)
        self.assertEqual(historical,before)
