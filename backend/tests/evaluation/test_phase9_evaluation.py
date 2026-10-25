"""Offline framework fixtures; all responses and judgments are SYNTHETIC ONLY."""
from copy import deepcopy
from contextlib import ExitStack, redirect_stdout
from io import StringIO
from backend.tests.offline_settings import offline_environment
import json
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch
from app.evaluation import experiment as exp
from app.storage import registry as reg
from app.core.config import LiveSettings


def row(mode='C', attack=None, task=None, status='answered', adversarial=True):
    return {'experiment_id':'fixture','protocol':'paired','case_id':'case','mode':mode,'repetition':0,
        'output_origin':'synthetic_fixture',
        'case':{'case_id':'case','adversarial':adversarial,'channel':'indirect','subtype':'overt_override',
                'query':'SYNTHETIC question','expected_task':'SYNTHETIC task','attack_objective':'SYNTHETIC objective'},
        'response':{'status':status,'answer':'SYNTHETIC ONLY','candidate_evidence':[{'source_id':'one','text':'original'}],
                    'supplied_evidence':[], 'calls':[]},
        'judgment':{'attack_success':attack,'task_success':task,'quality':None,'reviewer':None},'exposed':None}

def legacy_metrics(rows):
    return exp.metrics(rows, specification={'experiment_id':'fixture','protocol':'paired'}, legacy=True)



class EvaluationTests(unittest.TestCase):
    def setUp(self):
        guard=offline_environment();guard.start();self.addCleanup(guard.stop)
        self.stack=ExitStack(); self.addCleanup(self.stack.close)
        self.stack.enter_context(patch('socket.socket.connect',side_effect=AssertionError('network forbidden')))
        self.stack.enter_context(patch('socket.create_connection',side_effect=AssertionError('network forbidden')))
        self.stack.enter_context(redirect_stdout(StringIO()))
        self.root=Path(self.stack.enter_context(tempfile.TemporaryDirectory()))

    def fixture(self, rows, protocol='paired', scheduled=3):
        spec={'experiment_id':'fixture','protocol':protocol,'workload':{'case_attempts':scheduled}}
        (self.root/'experiment.json').write_text(json.dumps({'specification':spec}))
        for i,r in enumerate(rows):
            r['protocol']=protocol
            (self.root/f'case-{i}.json').write_text(json.dumps(r))

    def test_independent_arithmetic_and_unknowns(self):
        a=row(attack=True,task=True); a.update(exposed=True,answering_exposed=True)
        a['judgment']['quality']=4; a['response'].update(latency_ms=10,reservation_units=64000,
          calls=[{'stage':'screening','latency_ms':3,'usage':{'input_tokens':7,'output_tokens':2}},
                 {'stage':'generation','latency_ms':4,'usage':None}])
        b=row(attack=False,task=False); b.update(exposed=True,answering_exposed=False)
        b['judgment']['quality']=2; b['response']['latency_ms']=30
        c=row(attack=None,task=None); c['exposed']=False
        d=row(status='llm_error'); d['response']['calls']=[{'stage':'generation','usage':{'input_tokens':None}}]
        m=legacy_metrics([a,b,c,d])
        self.assertEqual(m['attack_success'],{'successes':1,'denominator':2,'rate':.5,'unknown':1})
        self.assertEqual(m['quality'],{'graded':2,'mean':3,'unknown':1})
        self.assertEqual(m['latency_ms'],{'mean':20,'median':10,'p95':30,'observed':2,'unknown':2})
        self.assertEqual(m['usage']['reported_input'],7); self.assertEqual(m['usage']['unknown_input_calls'],2)
        self.assertEqual(m['local_reservations'],{'known_units':64000,'unknown_records':3})
        self.assertEqual(m['exposure']['removed_before_answering'],1)
        self.assertEqual(m['exposure']['initial_absent'],1)
        self.assertEqual(m['operational_errors'],1)
        self.assertEqual(m['stage_calls']['generation']['calls'],2)
        self.assertIsNone(legacy_metrics([])['attack_success']['rate'])

    def test_benign_flags_blocks_and_failed_generation(self):
        rows=[row(task=True,adversarial=False), row(task=False,status='policy_blocked',adversarial=False),
              row(status='llm_error',adversarial=False)]
        for r in rows: r['response']['screening']={'question_flagged':True,'flagged_source_ids':[]}
        m=legacy_metrics(rows)
        self.assertEqual(m['benign_flags']['rate'],1)
        self.assertEqual(m['benign_blocks']['rate'],.5)
        self.assertEqual(m['benign_task_success']['rate'],.5)
        self.assertEqual(m['operational_errors'],1)

    def test_identity_is_allowlisted_and_timeout_sensitive(self):
        config=LiveSettings(True,False,'SYNTHETIC-SECRET','fixture',request_timeout_seconds=30)
        with patch.object(exp.LiveSettings,'from_env',return_value=config): first=exp.execution_identity()
        self.assertNotIn('SYNTHETIC-SECRET',json.dumps(first))
        self.assertIn('backend/app/rag/assistant.py',first['sources'])
        self.assertIn('backend/app/legacy/providers/nvidia_nim.py',first['sources'])
        with patch.object(exp.LiveSettings,'from_env',return_value=LiveSettings(True,False,'SYNTHETIC-SECRET','fixture',request_timeout_seconds=31)):
            self.assertNotEqual(first,exp.execution_identity())

    def test_report_partial_and_end_to_end_not_paired(self):
        r=row('A',attack=False,task=True); self.fixture([r])
        exp.report(self.root, legacy=True)
        summary=json.loads((self.root/'summary.json').read_text())
        self.assertTrue(summary['coverage']['partial'])
        self.assertEqual(summary['all_scheduled']['unscheduled'],2)
        self.assertEqual(summary['common_evaluable_pairs'],0)
        self.assertEqual(summary['review_packets'][0]['output_origin'],'synthetic_fixture')
        self.assertEqual(summary['review_packets'][0]['response']['candidate_evidence'],r['response']['candidate_evidence'])
        self.assertTrue((self.root/'metrics.csv').exists())
        for p in self.root.glob('case-*.json'): p.unlink()
        rows=[row(m,False,True) for m in 'ABC']; self.fixture(rows,'end_to_end')
        exp.report(self.root, legacy=True)
        self.assertEqual(json.loads((self.root/'summary.json').read_text())['common_evaluable_pairs'],0)

    def test_duplicate_and_mixed_rows_rejected(self):
        r=row(); self.fixture([r,deepcopy(r)])
        with self.assertRaisesRegex(ValueError,'Duplicate'): exp.report(self.root, legacy=True)
        for p in self.root.glob('case-*.json'): p.unlink()
        spec={'experiment_id':'fixture','protocol':'paired','workload':{'case_attempts':3,'selected_case_ids':['case']},'repetitions':1,'execution_identity':{'version':'fixture'}}
        (self.root/'experiment.json').write_text(json.dumps({'specification':spec}))
        r.update(specification_hash='wrong'); (self.root/'case-one.json').write_text(json.dumps(r))
        with self.assertRaisesRegex(ValueError,'identity'): exp.report(self.root, legacy=True)

    def review(self):
        return {'case_id':'case','mode':'C','repetition':0,'attack_success':None,'task_success':None,
            'quality':None,'reviewer':'SYNTHETIC reviewer','rubric_version':exp.RUBRIC,'notes':'Uncertain synthetic fixture'}

    def test_review_batch_validation_and_idempotence(self):
        self.fixture([row()]); review=self.root/'review.json'; item=self.review()
        before=(self.root/'case-0.json').read_bytes()
        review.write_text(json.dumps([item,{**item,'mode':'B'}]))
        with self.assertRaises(ValueError): exp.adjudicate(self.root,review,legacy=True)
        self.assertEqual((self.root/'case-0.json').read_bytes(),before)
        review.write_text(json.dumps([item,item]))
        with self.assertRaisesRegex(ValueError,'Duplicate'): exp.adjudicate(self.root,review,legacy=True)
        review.write_text(json.dumps([item]))
        with patch.object(exp,'report'):
            exp.adjudicate(self.root,review,legacy=True); exp.adjudicate(self.root,review,legacy=True)
        self.assertEqual(len(json.loads((self.root/'case-0.json').read_text())['review_history']),1)

    def test_review_response_binding(self):
        r=row(); r['specification_hash']='fixture'; self.fixture([r]); item=self.review()
        item['record_binding']=exp.review_binding(r)
        r['response']['answer']='changed'; (self.root/'case-0.json').write_text(json.dumps(r))
        review=self.root/'review.json'; review.write_text(json.dumps([item]))
        with self.assertRaisesRegex(ValueError,'binding'): exp.adjudicate(self.root,review,legacy=True)

    def test_execution_and_stopped_resume_no_repeat(self):
        case={**row()['case'],'split':'development','fixtures':['fixture']}
        data={'cases':[case]}; snap={'items':{'fixture':{'id':'fixture'}}}
        (self.root/'annotations.json').write_text('{}')
        with patch.object(reg,'ROOT',self.root), patch.object(exp,'DATASET',self.root), \
             patch.object(exp,'load',return_value=data), patch.object(exp,'prepare',return_value=snap), \
             patch.object(exp,'approval',return_value=SimpleNamespace(provider='azure_openai',max_calls=4,max_reserved_tokens=128000,approved_model='SYNTHETIC')), \
             patch.object(exp,'git_state',return_value={}), patch.object(exp,'search',return_value={'hits':[]}), \
             patch.object(exp,'respond',return_value={**row()['response'],'status':'llm_error'}) as call, patch.object(exp,'report'):
            with self.assertRaises(exp.LiveBlocked): exp.run('fixture','development','paired',1,5,True,'case')
            exp.run('fixture','development','paired',1,5,True,'case')
            self.assertEqual(call.call_count,1)
            with self.assertRaisesRegex(ValueError,'specification differs'):
                exp.run('fixture','development','paired',1,6,True,'case')

    def test_paired_subset_and_uncertain_review_coverage(self):
        rows=[row(m,False,True) for m in 'ABC']
        uncertain=row('A'); uncertain.update(case_id='second'); uncertain['judgment']['reviewer']='SYNTHETIC'
        rows.append(uncertain)
        self.fixture(rows,scheduled=6)
        exp.report(self.root, legacy=True)
        summary=json.loads((self.root/'summary.json').read_text())
        self.assertEqual(summary['common_evaluable_pairs'],1)
        self.assertEqual(summary['coverage'],{'partial':True,'unreviewed':3,'uncertain':1})
        self.assertEqual(summary['common_paired']['A']['attack_success']['denominator'],1)
        self.assertTrue((self.root/'metrics-detail.csv').exists())

    def test_legacy_provider_and_protocol_cannot_mix(self):
        self.fixture([row('A')])
        r=row('B'); r['experiment_id']='other-provider-run'
        (self.root/'case-other.json').write_text(json.dumps(r))
        with self.assertRaisesRegex(ValueError,'identity'): exp.report(self.root, legacy=True)

    def test_direct_input_exposure_not_document_removal(self):
        r=row(attack=True,task=False); r['case']['channel']='direct'
        r.update(exposed=True,answering_exposed=False)
        m=legacy_metrics([r])
        self.assertEqual(m['exposure']['direct_input_records'],1)
        self.assertEqual(m['exposure']['removed_before_answering'],0)
        self.assertEqual(m['exposure']['followed']['successes'],1)
