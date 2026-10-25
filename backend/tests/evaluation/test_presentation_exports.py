"""Synthetic fixture exports/review round trips; sockets forbidden."""
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from app.evaluation import experiment as exp
from backend.tests.evaluation.test_phase9_evaluation import row

def legacy_metrics(rows):
    return exp.metrics(rows, specification={'experiment_id':'fixture','protocol':'paired'}, legacy=True)



class PresentationTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.source=self.root/'source';self.source.mkdir()
        self.guard=patch('socket.socket.connect',side_effect=AssertionError('Network forbidden'))
        self.guard.start();self.addCleanup(self.guard.stop)

    def source_rows(self,rows):
        spec={'experiment_id':'fixture','protocol':'paired','output_origin':'synthetic_fixture',
              'workload':{'case_attempts':3}}
        (self.source/'experiment.json').write_text(json.dumps({'specification':spec}))
        for i,r in enumerate(rows):(self.source/f'case-{i}.json').write_text(json.dumps(r))

    def export(self,name='output'):
        output=self.root/name
        with redirect_stdout(io.StringIO()):exp.report(self.source,output,legacy=True)
        return output

    def test_empty_and_unreviewed_have_na_and_all_required_charts(self):
        self.source_rows([]);out=self.export()
        data=json.loads((out/'comparison.json').read_text())
        self.assertIn('SYNTHETIC',data['label'])
        self.assertTrue(all(r['asr'] is None and r['asr_denominator']==0 for r in data['rows']))
        self.assertTrue(all(r['scheduled_records']==1 and r['recorded_records']==0 for r in data['rows']))
        for name in ['asr','exposed_asr','benign_task_success','benign_false_flags','benign_false_blocks','quality','latency']:
            self.assertGreater((out/(name+'.png')).stat().st_size,1000)
        (self.source/'case-one.json').write_text(json.dumps(row('A')))
        partial=self.export('partial');summary=json.loads((partial/'summary.json').read_text())
        self.assertTrue(summary['coverage']['partial']);self.assertEqual(summary['coverage']['unreviewed'],1)
        self.assertIsNone(summary['by_mode']['A']['attack_success']['rate'])

    def test_export_preserves_source_and_template_roundtrip(self):
        record=row('C',adversarial=False);self.source_rows([record])
        before={p.name:p.read_bytes() for p in self.source.iterdir()}
        out=self.export()
        self.assertEqual(before,{p.name:p.read_bytes() for p in self.source.iterdir()})
        template=json.loads((out/'review-template.json').read_text())
        self.assertEqual(template[0]['record_binding'],exp.review_binding(record))
        self.assertEqual(template[0]['reviewer'],'')
        template[0].update(reviewer='SYNTHETIC REVIEW FIXTURE',notes='Arithmetic test, not actual human review',task_success=True,quality=4)
        review=self.root/'review.json';review.write_text(json.dumps(template))
        with patch.object(exp,'report'):exp.adjudicate(self.source,review,legacy=True)
        saved=json.loads((self.source/'case-0.json').read_text())
        self.assertTrue(saved['judgment']['task_success'])
        self.assertEqual(legacy_metrics([saved])['benign_task_success']['denominator'],1)
        with self.assertRaises(FileExistsError):self.export()
        with self.assertRaisesRegex(ValueError,'outside source'):
            exp.report(self.source,self.source/'nested',legacy=True)

    def test_tokens_reservations_and_error_unknowns_remain_separate(self):
        r=row('C',status='llm_error');r['response'].update(latency_ms=7,reservation_units=64000,
            calls=[{'stage':'screening','usage':{'input_tokens':5,'output_tokens':2}}, {'stage':'generation','usage':None}])
        self.source_rows([r]);out=self.export()
        metrics=json.loads((out/'summary.json').read_text())['by_mode']['C']
        self.assertEqual(metrics['usage']['reported_input'],5)
        self.assertEqual(metrics['usage']['unknown_input_calls'],1)
        self.assertEqual(metrics['local_reservations']['known_units'],64000)
        self.assertEqual(metrics['operational_errors'],1)
        self.assertEqual(metrics['attack_success']['denominator'],0)
        self.assertIn('unknown_input_calls',(out/'records.csv').read_text())

    def test_nonobject_review_rejected_before_writes(self):
        self.source_rows([row()]);before=(self.source/'case-0.json').read_bytes()
        review=self.root/'review.json';review.write_text('[null]')
        with self.assertRaisesRegex(ValueError,'must be an object'):exp.adjudicate(self.source,review,legacy=True)
        self.assertEqual((self.source/'case-0.json').read_bytes(),before)

    def test_review_packet_preserves_saved_scoring_provenance(self):
        r=row()
        self.assertIsNone(exp.review_packet(r)['scoring_spec_hash'])
        self.assertEqual(exp.review_packet(r,{'scoring_spec_hash':'SAVED-HISTORICAL-HASH'})['scoring_spec_hash'],
                         'SAVED-HISTORICAL-HASH')
        self.assertIsNone(exp.review_packet(r)['semantic_review'])

    def test_duplicate_review_keys_cannot_silently_replace_grade(self):
        self.source_rows([row()]);before=(self.source/'case-0.json').read_bytes()
        item={'case_id':'case','mode':'C','repetition':0,'attack_success':False,
              'task_success':None,'quality':4,'reviewer':'SYNTHETIC FIXTURE',
              'rubric_version':exp.RUBRIC,'notes':'Not actual human review'}
        text=json.dumps([item]).replace('"task_success": null','"task_success": false, "task_success": true')
        review=self.root/'review.json';review.write_text(text)
        with self.assertRaises(ValueError):exp.adjudicate(self.source,review,legacy=True)
        self.assertEqual((self.source/'case-0.json').read_bytes(),before)
