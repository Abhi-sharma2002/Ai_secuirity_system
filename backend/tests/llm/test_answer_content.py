"""Synthetic missing-answer regression; network forbidden, temporary ledger."""
from datetime import datetime,timedelta,timezone
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import httpx
from app.storage import registry as reg
from app.core.config import LiveSettings
from app.llm import client as live
from app.rag import assistant
from frontend.error_messages import describe_error

MODEL='synthetic-deployment'


class ContentTests(unittest.TestCase):
    def test_retired_reasoning_setting_does_not_change_azure_settings(self):
        with patch.dict('os.environ', {'LLM_BACKEND':'azure_openai','LIVE_LLM_ENABLED':'false',
                'AZURE_OPENAI_DEPLOYMENT':MODEL,'AZURE_OPENAI_ENDPOINT':'', 'NVIDIA_REASONING_EFFORT':'high'}, clear=True):
            self.assertIsNone(LiveSettings.from_env().reasoning_effort)

    def exercise(self,content,finish):
        seen=[]
        c=LiveSettings(True,False,'synthetic-only',MODEL,provider='azure_openai',
            base_url='https://offline.openai.azure.com/openai/v1')
        def transport(_transport,request):
            seen.append(request)
            p=json.loads(request.content)
            self.assertNotIn('reasoning_effort',p)
            self.assertEqual((p['max_completion_tokens'],p['temperature']),(700,1.0))
            return httpx.Response(200,request=request,headers={'x-request-id':'synthetic-request-id'},json={'id':'synthetic','choices':[{
                'message':{'role':'assistant','content':content,'reasoning_content':'DO_NOT_RECORD'},
                'finish_reason':finish}], 'usage':{'prompt_tokens':20,'completion_tokens':700,'total_tokens':720}})
        with tempfile.TemporaryDirectory() as folder,patch.object(reg,'ROOT',Path(folder)):
            reg.initialize()
            a=live.Approval(provider='azure_openai',allowance_id='SYNTHETIC',confirmed_free_promotional=True,
                approved_model=MODEL,approved_endpoint='https://offline.openai.azure.com/openai/v1',expires_at=datetime.now(timezone.utc)+timedelta(hours=1),max_calls=1,
                max_reserved_tokens=32000,chat_completions_supported=True,structured_outputs_supported=True,
                max_output_tokens_supported=True,confirmation_note='Synthetic only')
            with patch.object(live,'approval',return_value=a),patch.object(LiveSettings,'from_env',return_value=c), \
                 patch.object(live.diagnostics,'provenance',return_value={'credential_source':'synthetic'}), \
                 patch('socket.socket.connect',side_effect=AssertionError('Network forbidden')), \
                 patch('socket.create_connection',side_effect=AssertionError('Network forbidden')), \
                 patch.object(httpx.HTTPTransport,'handle_request',new=transport):
                result=assistant.respond('Question','B',initial={'hits':[{'id':'s','text':'Fact'}],'snapshot':[],'omitted_ids':[]})
            self.assertEqual(len(seen),1)
            record=result['calls'][0]
            self.assertEqual(record['http_status'],200)
            self.assertEqual(record['finish_reason'],finish)
            self.assertEqual(record['provider_request_id'],'synthetic-request-id')
            self.assertEqual(record['usage']['output_tokens'],700)
            self.assertNotIn('reasoning_effort',record['settings'])
            self.assertNotIn('DO_NOT_RECORD',json.dumps(record))
            with reg.connect() as db:
                row=db.execute('SELECT status,data FROM calls').fetchone()
            self.assertEqual(json.loads(row['data'])['reservation'],32000)
            return result,record

    def test_missing_text_retains_status_and_finish_reason(self):
        result,record=self.exercise(None,'length')
        self.assertEqual(result['status'],'llm_error')
        self.assertEqual(record['response_validation_error'],'non_text_content')
        self.assertFalse(record['answer_content_present'])
        self.assertIn('no usable final answer',describe_error(result))

    def test_valid_answer_still_parsed_and_cited(self):
        result,_=self.exercise(json.dumps({'status':'answered','answer':'SYNTHETIC ONLY','source_ids':['s']}),'stop')
        self.assertEqual(result['status'],'answered')
        self.assertEqual(result['references'][0]['id'],'s')

    def test_historical_error_has_clear_explanation(self):
        result={'calls':[{'exception_type':'ValueError','usage':{'output_tokens':700},'settings':{'max_output_tokens':700}}]}
        self.assertIn('no usable final answer',describe_error(result))
