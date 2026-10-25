"""Active Azure boundary regressions; fictional HTTP, sockets blocked, temp state."""
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from app.rag import assistant
from app.llm import client as live
from app.storage import registry as reg
from app.core.config import LiveSettings
from scripts.smoke_preflight import local_status
from backend.tests.llm import test_azure_openai as azure_fixtures
from backend.tests.llm.test_azure_openai import INITIAL, ANSWER, BASE, approval_values


class RuntimeCompletionTests(unittest.TestCase):
    def test_contradictory_reason_metadata_fails_closed(self):
        for reasons in (['none','forged_authority'],['secret_request','none']):
            decision={'question_flagged':False,'flagged_source_ids':[],'reason_codes':reasons}
            with self.subTest(reasons=reasons),azure_fixtures.AzureTests().session(screen=decision) as (observed,_,_):
                result=assistant.respond('Fictional question?','C',initial=INITIAL)
                self.assertEqual(result['status'],'screening_error')
                self.assertEqual(len(observed),1)
                self.assertIsNone(result['screening'])
                self.assertEqual(result['reservation_units'],64000)

    def test_preflight_cli_does_not_assign_historical_run_identity(self):
        import io
        from contextlib import redirect_stdout
        from scripts import smoke_preflight
        with tempfile.TemporaryDirectory() as tmp:
            output=Path(tmp)/'preflight.json'
            with patch('sys.argv',['preflight','--output',str(output)]), \
                 patch.object(smoke_preflight.exp,'plan',return_value={'SYNTHETIC':'workload'}), \
                 patch.object(smoke_preflight.LiveSettings,'from_env',return_value=SimpleNamespace()), \
                 patch.object(smoke_preflight,'local_status',return_value={'provider':'azure_openai'}), \
                 patch.object(smoke_preflight.exp.reg,'initialize',side_effect=AssertionError('No storage writes')), \
                 redirect_stdout(io.StringIO()):
                smoke_preflight.main()
            value=json.loads(output.read_text())
            self.assertIsNone(value['run_id']);self.assertIsNone(value['result_directory'])
            self.assertFalse(value['execution_identity_bound']);self.assertFalse(value['activation_performed'])

    def test_retired_destination_cannot_pass_azure_diagnostics(self):
        import httpx
        from app.llm import diagnostics
        for url in ('https://api.groq.com/openai/v1/chat/completions',
                    'https://integrate.api.nvidia.com/v1/chat/completions'):
            self.assertTrue(diagnostics.destination(httpx.Request('POST',url),BASE)['unexpected_destination'])

    def test_retired_credentials_are_not_consulted_for_active_diagnostics(self):
        from app.core.environment import credential_provenance
        with patch('dotenv.dotenv_values',side_effect=AssertionError('Retired credentials must not be inspected')):
            for provider in ('groq','nvidia_nim'):
                self.assertEqual(credential_provenance('SYNTHETIC',provider),
                    {'credential_source':'historical provider: inactive','credential_matches_root_env':False})

    def test_blank_answer_never_becomes_success(self):
        for mode in 'ABC':
            for text in ('',' \n\t'):
                with self.subTest(mode=mode,text=repr(text)), azure_fixtures.AzureTests().session(answer=ANSWER|{'answer':text}) as (observed,_,_):
                    result=assistant.respond('Fictional question?',mode,initial=INITIAL)
                    self.assertNotEqual(result['status'],'answered')
                    self.assertEqual(result['status'],'operational_error')
                    self.assertEqual(len(observed),2 if mode=='C' else 1)
                    self.assertEqual(result['reservation_units'],64000 if mode=='C' else 32000)
                    self.assertIsNotNone(result['calls'][-1]['usage'])

    def test_preflight_uses_azure_transport_not_retired_sdk(self):
        config=LiveSettings(True,False,'SYNTHETIC','SYNTHETIC',None,base_url=BASE)
        with patch('scripts.smoke_preflight.importlib.util.find_spec',side_effect=lambda name: object() if name=='httpx' else None) as find:
            status=local_status(config,{'maximum_api_calls_without_retries':4,'conservative_reserved_tokens':128000})
        self.assertEqual(status['provider'],'azure_openai')
        self.assertTrue(status['provider_transport_installed'])
        self.assertNotIn('provider_sdk_installed',status)
        find.assert_called_once_with('httpx')

    def test_preflight_rejects_historical_provider_and_endpoint_without_writes(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'approval.json'
            values=approval_values();config=LiveSettings(True,False,'SYNTHETIC',values['approved_model'],path,base_url=BASE)
            workload={'maximum_api_calls_without_retries':4,'conservative_reserved_tokens':128000}
            for mutation in ({'provider':'groq'},{'approved_endpoint':'https://different.openai.azure.com/openai/v1'},
                             {'deployment_model_version':None},{'activated_at':None,'entitlement_expiry':None}):
                with self.subTest(mutation=mutation):
                    values2={**values,**mutation}
                    if values2.get('activated_at') is None:values2['entitlement_expiry']=None
                    path.write_text(live.Approval(**values2).model_dump_json());before=path.read_bytes()
                    with patch('scripts.smoke_preflight.settings',SimpleNamespace(app_data_directory=Path(tmp)/'missing')):
                        status=local_status(config,workload)
                    self.assertFalse(status['local_approval_checks_pass'])
                    self.assertEqual(path.read_bytes(),before)
                    self.assertFalse((Path(tmp)/'missing').exists())

    def test_preflight_preserves_stop_on_old_approval_receipt(self):
        with tempfile.TemporaryDirectory() as tmp,patch.object(reg,'ROOT',Path(tmp)):
            reg.initialize();path=Path(tmp)/'approval.json'
            values=approval_values();approved=live.Approval(**values)
            old=hashlib.sha256(approved.model_dump_json().encode()).hexdigest()
            with reg.connect() as db:
                db.execute('INSERT INTO allowance VALUES(?,?,?,1)',(old,0,0))
                db.execute('INSERT INTO calls VALUES(?,?,?,?,?)',('SYNTHETIC',approved.allowance_id,'generation','completed',
                    json.dumps({'reservation':32000,'approval_fingerprint':old})))
            newer=approved.model_copy(update={'confirmation_note':'SYNTHETIC edited receipt, no stop bypass'})
            path.write_text(newer.model_dump_json())
            config=LiveSettings(True,False,'SYNTHETIC',approved.approved_model,path,base_url=BASE)
            database=Path(tmp)/'registry.sqlite3';before=database.read_bytes()
            with patch('scripts.smoke_preflight.settings',SimpleNamespace(app_data_directory=Path(tmp))):
                status=local_status(config,{'maximum_api_calls_without_retries':1,'conservative_reserved_tokens':32000})
            self.assertTrue(status['allowance_quota_stopped'])
            self.assertFalse(status['local_approval_checks_pass'])
            self.assertEqual(database.read_bytes(),before)
