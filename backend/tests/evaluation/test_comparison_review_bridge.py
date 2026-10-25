"""Synthetic temporary comparison → registry → import → review → exports. No network."""
from copy import deepcopy
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from app.storage import registry as reg
from app.api.runtime import Query, compare_query
from app.rag import comparison
from app.evaluation import comparison_provenance, comparison_review as bridge, experiment as exp
from app.evaluation.compatibility import validate, digest

QUESTION='How many fictional leave days?'
INITIAL={'hits':[{'id':'s1','text':'Fictional leave is 25 days.','version_id':'v1','document_id':'d1','filename':'synthetic.txt','page':0,'section':'body'}], 'snapshot':[{'id':'v1'}], 'omitted_ids':[]}
SETTINGS={'provider':'openrouter','api':'openrouter_chat_completions','configuration_version':'synthetic-profile',
          'temperature':'not sent','provider_seed':'not sent','max_retries':0}
PROFILE={'version':'interactive-review-provenance-v1','provider':'openrouter','model':'SYNTHETIC-NEMOTRON',
         'endpoint':'https://offline.invalid/chat/completions','routing':{'only':['Synthetic'], 'allow_fallbacks':False},
         'request_timeout_seconds':30,'screening_prompt_version':'synthetic-screen','stage_settings':{'generation':SETTINGS|{'max_output_tokens':1400},'screening':SETTINGS|{'max_output_tokens':700}},
         'defense_versions':{m:{'grounding':'test-ground','separation':'test-B' if m in 'BC' else None,'output_screening':'test-C' if m=='C' else None} for m in 'ABC'},
         'prompt_hash':comparison.PROMPT_HASH,'execution_identity':{'sources':{'synthetic.py':'test-hash'},'version':'synthetic'},
         'scoring_spec_hash':'synthetic-scoring-hash','rubric_version':exp.RUBRIC,'scoring_rules':{'version':'synthetic-benign-rules'}}
CRITERIA={'question':QUESTION,'expected_answer':'25 days','criteria_author':'SYNTHETIC FIXTURE','review_notes':'Synthetic task criterion only','adversarial':False}


def response(mode, status='answered'):
    stages=['screening','generation'] if mode=='C' else ['generation']
    if mode=='C' and status=='policy_blocked':stages=['screening']
    return {'mode':mode,'question':QUESTION,'status':status,'answer':'Synthetic: 25 days' if status=='answered' else 'Synthetic blocked/error',
            'references':deepcopy(INITIAL['hits']) if status=='answered' else [],'candidate_evidence':deepcopy(INITIAL['hits']),
            'supplied_evidence':[] if status=='policy_blocked' else deepcopy(INITIAL['hits']),
            'screening':{'question_flagged':status=='policy_blocked','flagged_source_ids':[],'reason_codes':['none']} if mode=='C' else None,
            'calls':[{'stage':s,'model':PROFILE['model'],'settings':deepcopy(PROFILE['stage_settings'][s]),
                      'usage':None if status=='llm_error' else {'input_tokens':10,'output_tokens':3,'total_tokens':13},
                      'attempts':1,'error':'synthetic_failure' if status=='llm_error' else None} for s in stages],
            'prompt_hash':PROFILE['prompt_hash'],'defense_versions':deepcopy(PROFILE['defense_versions'][mode]),
            'snapshot':deepcopy(INITIAL['snapshot']),'omitted_ids':[],'latency_ms':50,'reservation_units':64000 if mode=='C' else 32000,
            'reservation_ids':['synthetic-'+mode+'-'+str(i) for i in range(2 if mode=='C' else 1)]}


class BridgeTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.out=self.root/'exports'
        for target,value in [('socket.socket.connect',AssertionError('network forbidden')),('socket.create_connection',AssertionError('network forbidden'))]:
            p=patch(target,side_effect=value);p.start();self.addCleanup(p.stop)
        p=patch.object(reg,'ROOT',self.root/'data');p.start();self.addCleanup(p.stop)
        p=redirect_stdout(io.StringIO());p.__enter__();self.addCleanup(p.__exit__,None,None,None)
        reg.initialize();self.db=reg.ROOT/'registry.sqlite3'

    def saved(self, request='synthetic-comparison', failure=None):
        def reply(question,mode,**kwargs):return response(mode, failure[1] if failure and mode==failure[0] else 'answered')
        with patch.object(comparison.live,'approval',return_value=SimpleNamespace()), patch.object(comparison.live,'allowance_capacity',return_value={'stopped':False,'remaining_calls':4,'remaining_reserved_tokens':128000}), patch.object(comparison,'search',return_value=deepcopy(INITIAL)), patch.object(comparison.live,'validate_interactive_input'), patch.object(comparison,'respond',side_effect=reply), patch.object(comparison_provenance,'capture',return_value=deepcopy(PROFILE)):
            value=compare_query(Query(question=QUESTION,request_id=request))
        value['output_origin']='synthetic_fixture'
        value['source_record_binding']=digest({k:v for k,v in value.items() if k!='source_record_binding'})
        with reg.connect() as db:db.execute('UPDATE requests SET result=? WHERE id=?',(json.dumps(value),request))
        return value

    def imported(self, **kwargs):
        self.saved(**kwargs)
        return bridge.import_saved(self.db, kwargs.get('request','synthetic-comparison'),CRITERIA,self.out)

    def test_full_review_roundtrip_and_charts_preserve_source(self):
        source=self.saved();before=self.db.read_bytes()
        folder=bridge.import_saved(self.db,'synthetic-comparison',CRITERIA,self.out,exported=source)
        self.assertEqual(self.db.read_bytes(),before)
        rows=exp.saved_rows(folder,json.loads((folder/'experiment.json').read_text())['specification'])
        self.assertTrue(all(r['judgment']['reviewer'] is None for r in rows))
        self.assertEqual({r['mode']:r['response'] for r in rows},source['results'])
        summary=json.loads((folder/'summary.json').read_text())
        self.assertIn('INTERACTIVE COMPARISON',summary['presentation']['label'])
        self.assertIn('SYNTHETIC',summary['presentation']['label'])
        self.assertEqual(summary['presentation']['provider'],'openrouter')
        self.assertEqual(summary['presentation']['model'],'SYNTHETIC-NEMOTRON')
        self.assertIsNone(summary['by_mode']['A']['benign_task_success']['rate'])
        original=(folder/'source-comparison.json').read_bytes()
        template=json.loads((folder/'review-template.json').read_text())
        for item in template:item.update(task_success=True,quality=4,reviewer='SYNTHETIC TEST REVIEWER',notes='Fixture judgment only; no real approval')
        review=self.root/'judgments.json';review.write_text(json.dumps(template));exp.adjudicate(folder,review)
        updated=json.loads((folder/'summary.json').read_text())
        self.assertEqual(updated['common_evaluable_pairs'],1)
        self.assertEqual(updated['by_mode']['A']['benign_task_success']['denominator'],1)
        self.assertIsNone(updated['by_mode']['A']['attack_success']['rate'])
        self.assertEqual((folder/'source-comparison.json').read_bytes(),original)
        self.assertEqual(len(list(folder.glob('*.png'))),7)
        target=self.root/'new-report';exp.report(folder,target)
        self.assertTrue((target/'records.csv').exists())
        current=exp.saved_rows(folder,json.loads((folder/'experiment.json').read_text())['specification'])
        altered=deepcopy(current);altered[0]['response']['answer']='altered after review'
        with self.assertRaisesRegex(ValueError,'binding'):exp.metrics(altered)
        with self.assertRaises(FileExistsError):bridge.import_saved(self.db,'synthetic-comparison',CRITERIA,self.out)

    def test_partial_failure_and_screening_block(self):
        for name,failure in [('partial',('B','llm_error')),('blocked',('C','policy_blocked'))]:
            folder=self.imported(request='synthetic-'+name,failure=failure)
            summary=json.loads((folder/'summary.json').read_text())
            self.assertEqual(summary['record_coverage']['unexecuted_records'],1 if name=='partial' else 0)
            if name=='partial':
                self.assertEqual(summary['by_mode']['B']['operational_errors'],1)
                self.assertEqual(summary['by_mode']['B']['benign_task_success']['denominator'],0)
                items=json.loads((folder/'review-template.json').read_text())
                for i in items:i.update(task_success=True,quality=4,reviewer='Synthetic',notes='fixture')
                file=self.root/'bad-review.json';file.write_text(json.dumps(items))
                before={p.name:p.read_bytes() for p in folder.glob('case-*.json')}
                with self.assertRaisesRegex(ValueError,'Operational errors'):exp.adjudicate(folder,file)
                self.assertEqual(before,{p.name:p.read_bytes() for p in folder.glob('case-*.json')})
            else:self.assertEqual(summary['by_mode']['C']['benign_blocks']['rate'],1)

    def test_missing_and_altered_provenance_rejected(self):
        source=self.saved();changed=deepcopy(source);changed['results']['A']['answer']='tamper'
        with self.assertRaisesRegex(ValueError,'authoritative'):bridge.import_saved(self.db,'synthetic-comparison',CRITERIA,self.out,exported=changed)
        source.pop('review_provenance')
        with reg.connect() as db:db.execute('UPDATE requests SET result=? WHERE id=?',(json.dumps(source),'synthetic-comparison'))
        with self.assertRaisesRegex(ValueError,'provenance'):bridge.import_saved(self.db,'synthetic-comparison',CRITERIA,self.out)

    def test_tampered_import_rejected_before_review_writes(self):
        folder=self.imported();file=folder/'case-A.json';row=json.loads(file.read_text());row['response']['answer']='tampered';file.write_text(json.dumps(row))
        with self.assertRaises(ValueError):exp.report(folder,self.root/'bad-export')
        self.assertFalse((self.root/'bad-export').exists())
        with self.assertRaises(ValueError):exp.adjudicate(folder,folder/'review-template.json')

    def test_mixed_identity_fails_even_in_one_mode(self):
        folder=self.imported();spec=json.loads((folder/'experiment.json').read_text())['specification'];rows=exp.saved_rows(folder,spec)
        for field,value in [('provider','azure_openai'),('model','other-model'),('scoring_spec_hash','changed'),('execution_identity',{'version':'other'}),('defense_versions',{}),('request_timeout_seconds',90),('routing',{'only':['Other']})]:
            mixed=deepcopy(rows);mixed[1]['aggregation_identity'][field]=value
            with self.assertRaises(ValueError):exp.metrics(mixed)
        for field,value in [('temperature',0),('max_output_tokens',700),('provider_seed',42)]:
            mixed=deepcopy(rows);mixed[1]['response']['calls'][0]['settings'][field]=value
            with self.assertRaises(ValueError):exp.metrics(mixed)
        self.assertEqual(exp.metrics(rows)['benign_task_success']['denominator'],0)

    def test_legacy_explicit_single_run(self):
        from backend.tests.evaluation.test_phase9_evaluation import row
        r=row(adversarial=False);spec={'experiment_id':'fixture','protocol':'paired'}
        r['response']['calls']=[{'stage':'generation','model':'historical-model','settings':{'provider':'azure_openai'},'usage':None}]
        with self.assertRaises(ValueError):exp.metrics([r])
        self.assertEqual(exp.metrics([r],specification=spec,legacy=True)['operational_errors'],0)
        other=deepcopy(r);other['response']['calls'][0]['settings']['provider']='openrouter'
        with self.assertRaises(ValueError):exp.metrics([r,other],specification=spec,legacy=True)
        other=deepcopy(r);other['experiment_id']='other-run'
        with self.assertRaises(ValueError):exp.metrics([r,other],specification=spec,legacy=True)

    def test_no_execution_and_mismatched_initial_evidence(self):
        source=self.saved();source.update(results={},status='insufficient_evidence',not_executed_modes=list('ABC'))
        source['initial_evidence']['hits']=[]
        source['source_record_binding']=digest({k:v for k,v in source.items() if k!='source_record_binding'})
        with reg.connect() as db:db.execute('UPDATE requests SET result=? WHERE id=?',(json.dumps(source),'synthetic-comparison'))
        folder=bridge.import_saved(self.db,'synthetic-comparison',CRITERIA,self.out)
        summary=json.loads((folder/'summary.json').read_text())
        self.assertEqual(summary['record_coverage']['unexecuted_records'],3)
        self.assertIsNone(summary['by_mode']['C']['attack_success']['rate'])
        changed=deepcopy(source);changed['results']={'A':response('A')};changed['not_executed_modes']=['B','C'];changed['status']='partial'
        changed['source_record_binding']=digest({k:v for k,v in changed.items() if k!='source_record_binding'})
        with self.assertRaisesRegex(ValueError,'initial evidence'):bridge.validate_comparison(changed,'synthetic-comparison')

    def test_legacy_export_is_labeled_and_source_preserved(self):
        from backend.tests.evaluation.test_phase9_evaluation import row
        source=self.root/'legacy';source.mkdir()
        spec={'experiment_id':'fixture','protocol':'paired','settings':{'provider':'azure_openai'},'model':'SYNTHETIC-OLD', 'workload':{'case_attempts':3}}
        (source/'experiment.json').write_text(json.dumps({'specification':spec}))
        (source/'case-A.json').write_text(json.dumps(row('A',adversarial=False)))
        before={p.name:p.read_bytes() for p in source.iterdir()}
        with self.assertRaisesRegex(ValueError,'provenance'):exp.report(source,self.root/'invalid')
        exp.report(source,self.root/'historical-export',legacy=True)
        summary=json.loads((self.root/'historical-export/summary.json').read_text())
        self.assertIn('LEGACY SINGLE RUN',summary['presentation']['label'])
        self.assertEqual(before,{p.name:p.read_bytes() for p in source.iterdir()})

    def test_saved_response_seal_and_forged_unapproved_grades(self):
        source=self.saved();source['results']['A']['answer']='Changed after save'
        with self.assertRaisesRegex(ValueError,'binding'):bridge.validate_comparison(source,'synthetic-comparison')
        folder=bridge.import_saved(self.db,'synthetic-comparison',CRITERIA,self.out)
        rows=exp.saved_rows(folder,json.loads((folder/'experiment.json').read_text())['specification'])
        rows[0]['judgment']['task_success']=True
        with self.assertRaisesRegex(ValueError,'Unapproved'):exp.metrics(rows)

    def test_captured_profile_matches_public_current_settings(self):
        config=SimpleNamespace(provider='openrouter',model='SYNTHETIC-NEMOTRON',base_url='https://offline.invalid',request_timeout_seconds=30)
        with patch.object(comparison_provenance.LiveSettings,'from_env',return_value=config), patch.object(exp,'execution_identity',return_value={'sources':{'test.py':'synthetic-hash'}}):
            profile=comparison_provenance.capture('synthetic-prompt-hash')
        self.assertEqual(profile['stage_settings']['generation']['max_output_tokens'],1400)
        self.assertEqual(profile['stage_settings']['screening']['max_output_tokens'],700)
        self.assertEqual(profile['routing'],{'only':['Nvidia'],'allow_fallbacks':False})
        self.assertNotIn('api_key',profile)
        self.assertEqual(profile['stage_settings']['generation']['temperature'],'not sent')

    def test_cli_import_and_review(self):
        from scripts import import_comparison, review_saved_comparison
        self.saved()
        criteria_file=self.root/'criteria.json';criteria_file.write_text(json.dumps(CRITERIA))
        with patch('sys.argv',['import_comparison','--request-id','synthetic-comparison','--database',str(self.db),'--criteria',str(criteria_file),'--output-root',str(self.out)]):
            import_comparison.main()
        folder=self.out/('interactive-'+digest('synthetic-comparison')[:24])
        items=json.loads((folder/'review-template.json').read_text())
        for item in items:item.update(reviewer='SYNTHETIC CLI TEST',notes='Test only',task_success=True,quality=4)
        file=self.root/'reviewed.json';file.write_text(json.dumps(items))
        with patch('sys.argv',['review_saved_comparison','--source',str(folder),'--judgments',str(file)]):
            review_saved_comparison.main()
        self.assertEqual(json.loads((folder/'summary.json').read_text())['coverage']['unreviewed'],0)
