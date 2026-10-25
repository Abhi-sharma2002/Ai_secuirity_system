"""Offline development smoke selection/gate tests. All transport/response doubles labeled."""
from backend.tests.offline_settings import offline_environment
import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

from fastapi.testclient import TestClient
from app.storage import registry as reg
from app.core.config import LiveSettings
from app.evaluation import experiment as exp
from app.llm import client as live
from app.main import app
from scripts.smoke_preflight import CASE_IDS, local_status


class SmokePlanningTests(unittest.TestCase):
    def setUp(self):
        guard=offline_environment();guard.start();self.addCleanup(guard.stop)
        self.data={'cases':[{'case_id':cid,'split':'development','fixtures':[cid],
            'query':'TEST QUESTION','channel':None,'adversarial':False} for cid in CASE_IDS]+
            [{'case_id':'final-01','split':'final'}]}
        guard=patch('socket.socket.connect',side_effect=AssertionError('Network forbidden'))
        guard.start();self.addCleanup(guard.stop)

    def test_three_cases_have_nine_attempts_twelve_calls_and_correct_tokens(self):
        with patch.object(exp,'load',return_value=self.data):
            p=exp.plan('development',1,case_ids=CASE_IDS)
        self.assertEqual(p['selected_case_ids'],CASE_IDS)
        self.assertEqual(p['case_attempts'],9)
        self.assertEqual(p['maximum_api_calls_without_retries'],12)
        self.assertEqual(p['conservative_reserved_tokens'],384000)

    def test_cli_subset_plan_never_executes_and_cannot_select_final(self):
        with tempfile.TemporaryDirectory() as folder,patch.object(reg,'ROOT',Path(folder)), \
             patch.object(exp,'load',return_value=self.data),patch.object(exp,'approval') as approval, \
             patch.object(exp,'respond') as respond,redirect_stdout(io.StringIO()) as out, \
             patch('sys.argv',['experiment','plan','--split','development','--case-ids',*CASE_IDS]):
            exp.main()
            self.assertEqual(json.loads(out.getvalue())['selected_case_ids'],CASE_IDS)
            approval.assert_not_called();respond.assert_not_called()
        for split,ids in [('final',CASE_IDS),('development',['final-01']),
                          ('development',[CASE_IDS[0],'missing']),('development',[]),
                          ('development',[CASE_IDS[0],CASE_IDS[0]])]:
            with self.subTest(split=split,ids=ids),patch.object(exp,'load',return_value=self.data):
                with self.assertRaises(ValueError):exp.plan(split,1,case_ids=ids)

    def test_dry_run_never_reads_approval_or_creates_results(self):
        with tempfile.TemporaryDirectory() as folder,patch.object(reg,'ROOT',Path(folder)), \
             patch.object(exp,'load',return_value=self.data),patch.object(exp,'approval') as approval, \
             patch.object(exp,'prepare') as prepare,redirect_stdout(io.StringIO()):
            exp.run('TEST','development','paired',1,42,False,case_ids=CASE_IDS)
            approval.assert_not_called();prepare.assert_not_called()
            self.assertFalse((Path(folder)/'experiments').exists())

    def test_selected_run_stops_after_operational_error_and_preserves_record(self):
        # Explicit response/retrieval/approval doubles, no real provider authorization.
        for status,error in [('screening_error','invalid_screening_schema_or_ids'),
                             ('llm_error','unavailable_model'),('live_blocked','exhausted')]:
            with self.subTest(status=status),tempfile.TemporaryDirectory() as folder:
                root=Path(folder); (root/'annotations.json').write_text('{}')
                with patch.object(reg,'ROOT',root/'runtime'),patch.object(exp,'DATASET',root), \
                     patch.object(exp,'load',return_value=self.data), \
                     patch.object(exp,'approval',return_value=SimpleNamespace(max_calls=12,max_reserved_tokens=384000,approved_model='TEST')), \
                     patch.object(exp,'prepare',return_value={'items':{cid:{'id':cid} for cid in CASE_IDS}}), \
                     patch.object(exp,'search',return_value={'hits':[],'snapshot':[],'omitted_ids':[]}), \
                     patch.object(exp,'respond',return_value={'status':status,'error':error,'calls':[]}) as respond, \
                     patch.object(exp,'report'),redirect_stdout(io.StringIO()):
                    reg.initialize()
                    with self.assertRaisesRegex(live.LiveBlocked,'Run stopped'):
                        exp.run('TEST','development','paired',1,42,True,case_ids=CASE_IDS)
                    self.assertEqual(respond.call_count,1)
                    results=list((reg.ROOT/'experiments/TEST').glob('case-*.json'))
                    self.assertEqual(len(results),1)
                    self.assertEqual(json.loads(results[0].read_text())['response']['status'],status)
                    spec=json.loads((reg.ROOT/'experiments/TEST/experiment.json').read_text())['specification']
                    self.assertEqual(spec['case_ids'],sorted(CASE_IDS))
                    self.assertEqual(spec['execution_policy'],'stop_on_operational_failure_v1')
                    with self.assertRaisesRegex(ValueError,'Resume specification differs'):
                        exp.run('TEST','development','paired',1,42,True,case_ids=CASE_IDS[:2])
                    self.assertEqual(respond.call_count,1)

    def test_invalid_approval_stops_before_index_or_model(self):
        with patch.object(exp,'load',return_value=self.data), \
             patch.object(exp,'approval',side_effect=live.LiveBlocked('TEST invalid approval')), \
             patch.object(exp,'prepare') as prepare,patch.object(exp,'respond') as respond,redirect_stdout(io.StringIO()):
            with self.assertRaises(live.LiveBlocked):
                exp.run('TEST','development','paired',1,42,True,case_ids=CASE_IDS)
            prepare.assert_not_called();respond.assert_not_called()

    def test_schema_errors_cannot_echo_secrets(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'approval.json';path.write_text('{"provider":"DO-NOT-ECHO-SECRET"}')
            config=LiveSettings(True,False,'DO-NOT-ECHO-KEY','',path)
            result=local_status(config,{'maximum_api_calls_without_retries':12,'conservative_reserved_tokens':384000})
            self.assertFalse(result['allowance_schema_valid'])
            self.assertNotIn('DO-NOT-ECHO',json.dumps(result))

    def test_local_allowance_checks_expiry_model_and_remaining_usage_read_only(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);path=root/'approval.json'
            now=datetime.now(timezone.utc)
            endpoint='https://synthetic.openai.azure.com/openai/v1'
            a=live.Approval(provider='azure_openai',allowance_id='TEST ONLY',confirmed_free_promotional=True,
                approved_model='TEST MODEL',approved_endpoint=endpoint,deployment_model_version='SYNTHETIC MODEL/VERSION',
                eligibility_evidence='SYNTHETIC eligibility fixture only',eligibility_checked_at=now,activated_at=now,
                entitlement_expiry='unknown',expires_at=now+timedelta(hours=1),
                max_calls=12,max_reserved_tokens=384000,chat_completions_supported=True,
                structured_outputs_supported=True,max_output_tokens_supported=True,confirmation_note='OFFLINE TEST ONLY')
            path.write_text(a.model_dump_json())
            config=LiveSettings(True,False,'TEST KEY','TEST MODEL',path,provider='azure_openai',base_url=endpoint)
            config_settings=SimpleNamespace(app_data_directory=root/'runtime')
            with patch('scripts.smoke_preflight.settings',config_settings):
                workload={'maximum_api_calls_without_retries':12,'conservative_reserved_tokens':384000}
                self.assertTrue(local_status(config,workload)['local_approval_checks_pass'])
                self.assertFalse((root/'runtime').exists())
                config=LiveSettings(True,False,'TEST KEY','DIFFERENT MODEL',path,provider='azure_openai',base_url=endpoint)
                self.assertFalse(local_status(config,workload)['allowance_model_matches'])
                expired=a.model_copy(update={'expires_at':datetime.now(timezone.utc)-timedelta(hours=1)})
                path.write_text(expired.model_dump_json())
                self.assertFalse(local_status(config,workload)['allowance_not_expired'])
                path.write_text(a.model_dump_json())
                with patch.object(reg,'ROOT',root/'runtime'):
                    reg.initialize()
                    with reg.connect() as db:
                        db.execute('INSERT INTO calls VALUES(?,?,?,?,?)',('TEST','TEST ONLY','generation','completed',json.dumps({'reservation':32000})))
                before=path.read_bytes()
                result=local_status(LiveSettings(True,False,'TEST KEY','TEST MODEL',path,provider='azure_openai',base_url=endpoint),workload)
                self.assertFalse(result['allowance_remaining_budget_sufficient'])
                self.assertEqual(before,path.read_bytes())


class SmokeAPITests(unittest.TestCase):
    def test_ready_and_disabled_chat_are_secret_safe_and_backend_scope_only(self):
        # Explicit retrieval double only; real API/shared assistant gate/idempotency, no provider answer.
        with tempfile.TemporaryDirectory() as folder,patch.object(reg,'ROOT',Path(folder)), \
             patch.dict(os.environ,{'FREE_ONLY':'true','LIVE_LLM_ENABLED':'false',
                 'LLM_BACKEND':'azure_openai','AZURE_OPENAI_API_KEY':'TEST-SECRET-KEY','AZURE_OPENAI_DEPLOYMENT':'', 'AZURE_OPENAI_ENDPOINT':'', 'AZURE_OPENAI_ALLOWANCE_FILE':''}), \
             patch('app.rag.assistant.search',return_value={'hits':[{'id':'source','text':'TEST source'}],
                 'snapshot':[],'omitted_ids':[]}) as search, \
             patch.object(live,'call',side_effect=AssertionError('Provider forbidden')) as call:
            with TestClient(app) as api:
                response=api.get('/ready'); self.assertEqual(response.status_code,200)
                self.assertFalse(response.json()['live']['enabled'])
                query={'question':'TEST employee question','mode':'C','request_id':str(uuid4())}
                response=api.post('/chat',json=query)
                self.assertEqual(response.json()['status'],'live_blocked')
                self.assertNotIn('TEST-SECRET-KEY',response.text)
                self.assertEqual(api.post('/chat',json=query).json(),response.json())
                self.assertEqual(search.call_count,1);call.assert_not_called()
                self.assertEqual(api.post('/chat',json={**query,'collection':'benchmark'}).status_code,422)
