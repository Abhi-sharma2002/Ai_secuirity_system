"""Offline semantic-version/review plumbing; no model behavior assertions."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from app.evaluation import experiment as exp, semantics
from backend.tests.evaluation.test_phase9_evaluation import row


class Phase12SemanticsTests(unittest.TestCase):
    def test_approved_scope_and_pending_rubric(self):
        frozen = semantics.snapshot()
        rules = frozen['rules']
        self.assertEqual(rules['approval']['approved'], ['P12-01','P12-02','P12-03','P12-04','P12-06'])
        self.assertEqual(rules['approval']['pending'], ['P12-05'])
        self.assertFalse(rules['legacy_screening_annotations']['E037']['task_rubric_changed'])
        for cid in ('development-12','final-30'):
            disclosure = semantics.criteria(frozen,cid)['case_annotations']['disclosure']
            self.assertEqual(disclosure['designated_fictional_marker'],'CANARY-LAB-8041')
            self.assertTrue(disclosure['human_review_required'])
        self.assertFalse(rules['dataset_role']['untouched_holdout'])

    def test_binding_drift_refused_and_old_review_binding_unchanged(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp)/'rules.json'
            changed = deepcopy(semantics.snapshot()['rules'])
            changed['bindings']['backend/benchmark/annotations.json'] = '0'*64
            source.write_text(json.dumps(changed))
            with patch.object(semantics,'RULES',source), self.assertRaisesRegex(ValueError,'inputs changed'):
                semantics.snapshot()
        original = row()
        old = exp.digest({k:original.get(k) for k in ('experiment_id','specification_hash','case_id','mode','repetition','case','response','output_origin')})
        self.assertEqual(exp.review_binding(original),old)
        self.assertIsNone(exp.review_packet(original)['semantic_review'])

    def test_saved_criteria_and_component_spans_bound_to_review(self):
        frozen = semantics.snapshot()
        for cid in ('development-11','final-20','final-26'):
            criteria = semantics.criteria(frozen,cid)
            self.assertEqual({p['name'] for p in criteria['case_annotations']['component_locations']},
                             {'continuation_cue','standalone_override'})
        record = row()
        record['semantic_review'] = semantics.criteria(frozen,'development-12')
        before = exp.review_binding(record)
        record['semantic_review']['case_annotations']['task_oracle'] = 'CHANGED TEST VALUE'
        self.assertNotEqual(exp.review_binding(record),before)

    def test_component_review_preserves_full_span_metrics_and_validates_atomically(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            (folder/'experiment.json').write_text(json.dumps({'specification':{'experiment_id':'fixture','protocol':'paired','workload':{'case_attempts':1}}}))
            record = row(attack=False,task=True)
            record['case_id'] = 'development-11'
            record['semantic_review'] = semantics.criteria(semantics.snapshot(),'development-11')
            record['specification_hash'] = 'SYNTHETIC'
            record['exposed'] = False
            path = folder/'case-synthetic.json'; path.write_text(json.dumps(record))
            item = {'case_id':'development-11','mode':'C','repetition':0,
                    'attack_success':False,'task_success':True,'quality':4,
                    'reviewer':'SYNTHETIC TEST REVIEWER','rubric_version':exp.RUBRIC,
                    'notes':'SYNTHETIC schema/arithmetic fixture, not a human observation.',
                    'record_binding':exp.review_binding(record),
                    'component_exposure':{'candidate':{'continuation_cue':False,'standalone_override':True},
                                          'supplied':{'continuation_cue':None,'standalone_override':None}}}
            review = folder/'review.json'
            bad = deepcopy(item);bad['component_exposure']['candidate']['standalone_override'] = 1
            review.write_text(json.dumps([bad])); before = path.read_bytes()
            with patch.object(exp,'report'), self.assertRaisesRegex(ValueError,'boolean/null'):
                exp.adjudicate(folder,review,legacy=True)
            self.assertEqual(path.read_bytes(),before)
            review.write_text(json.dumps([item]))
            with patch.object(exp,'report'):
                exp.adjudicate(folder,review,legacy=True)
            saved = json.loads(path.read_text())
            self.assertFalse(saved['exposed'])
            self.assertEqual(exp.metrics([saved],specification={'experiment_id':'fixture','protocol':'paired'},legacy=True)['exposed_attack_success']['denominator'],0)
            self.assertEqual(saved['judgment']['component_exposure'],item['component_exposure'])
            historical = deepcopy(record);historical.pop('semantic_review')
            path.write_text(json.dumps(historical));item['record_binding']=exp.review_binding(historical)
            review.write_text(json.dumps([item]))
            with patch.object(exp,'report'), self.assertRaisesRegex(ValueError,'frozen component schema'):
                exp.adjudicate(folder,review,legacy=True)

    def test_new_records_must_match_frozen_criteria(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            frozen = semantics.snapshot()
            spec = {'experiment_id':'fixture','protocol':'paired','semantic_rules':frozen,'workload':{}}
            record = row(); record['semantic_review'] = semantics.criteria(frozen,record['case_id'])
            path = folder/'case-synthetic.json';path.write_text(json.dumps(record))
            self.assertEqual(len(exp.saved_rows(folder,spec)),1)
            record['semantic_review']['sha256'] = 'SYNTHETIC DRIFT'
            path.write_text(json.dumps(record))
            with self.assertRaisesRegex(ValueError,'semantic criteria differ'):
                exp.saved_rows(folder,spec)
