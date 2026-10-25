"""Offline actual-adapter request assembly; dummy credentials, synthetic transport.
Request assembly uses only dummy credentials; production ledger is untouched.
"""
import json
import tempfile
import unittest
from datetime import datetime,timedelta,timezone
from pathlib import Path
from unittest.mock import patch
import httpx
from app.core import registry as reg
from app.core.config import LiveSettings
from app.llm import client as live
from app.rag.assistant import Answer


class GroqEndpointTests(unittest.TestCase):
    def exercise(self, status, error_body=None, non_json=False):
        observed=[]
        dummy='OFFLINE-DUMMY-CREDENTIAL-ONLY'
        def transport(self_transport,request):
            # Assert only booleans to avoid exposing any header values on failure.
            observed.append(str(request.url))
            self.assertTrue(str(request.url)=='https://api.groq.com/openai/v1/chat/completions','Unexpected provider URL')
            self.assertTrue(request.method=='POST','Unexpected HTTP method')
            self.assertTrue(request.headers.get('authorization')=='Bearer '+dummy,'Explicit dummy credential did not reach SDK')
            self.assertTrue(len(request.headers.get_list('authorization'))==1,'Duplicate auth header')
            self.assertFalse('cookie' in request.headers,'Unexpected cookie')
            self.assertFalse(request.url.query,'Unexpected query')
            self.assertFalse('x-api-key' in request.headers,'Unexpected alternative auth')
            payload=json.loads(request.content)
            self.assertEqual(payload['model'],'offline-test-model')
            self.assertEqual(payload['max_tokens'],700)
            self.assertTrue(payload['response_format']['json_schema']['strict'])
            if status == 307:
                return httpx.Response(307,headers={'location':'https://example.invalid/redirect'},request=request)
            if status==401:
                if non_json:
                    return httpx.Response(401,text='Not JSON: '+dummy,headers={'x-request-id':'req_synthetic_401'},request=request)
                return httpx.Response(401,json=error_body if error_body is not None else
                    {'error':{'message':'Invalid API key','type':'authentication_error','code':'invalid_api_key'}},
                    headers={'x-request-id':'req_synthetic_401'},request=request)
            return httpx.Response(200,json={'id':'SYNTHETIC-OFFLINE','object':'chat.completion','created':0,
                'model':'offline-test-model','choices':[{'index':0,'finish_reason':'stop','message':{'role':'assistant',
                'content':json.dumps({'status':'answered','answer':'EXPLICIT SYNTHETIC RESPONSE','source_ids':['TEST-SOURCE']})}}],
                'usage':{'prompt_tokens':5,'completion_tokens':5,'total_tokens':10}},request=request)
        with tempfile.TemporaryDirectory() as folder,patch.object(reg,'ROOT',Path(folder)):
            reg.initialize()
            approved=live.Approval(provider='groq',allowance_id='OFFLINE-ENDPOINT-TEST',confirmed_free_promotional=True,
                approved_model='offline-test-model',expires_at=datetime.now(timezone.utc)+timedelta(hours=1),max_calls=1,
                max_reserved_tokens=32000,chat_completions_supported=True,structured_outputs_supported=True,
                max_output_tokens_supported=True,confirmation_note='EXPLICIT TEST ONLY; not an account approval')
            config=LiveSettings(True,True,dummy,'offline-test-model')
            with patch.object(live,'approval',return_value=approved),patch.object(live.LiveSettings,'from_env',return_value=config), \
                 patch.dict('os.environ',{'GROQ_API_BASE':'https://example.invalid/ignored','GROQ_BASE_URL':'https://example.invalid/ignored','GROQ_API_KEY':'UNRELATED-OFFLINE-DUMMY'}), \
                 patch('socket.socket.connect',side_effect=AssertionError('Network forbidden')), \
                 patch('socket.create_connection',side_effect=AssertionError('Network forbidden')), \
                 patch.object(httpx.HTTPTransport,'handle_request',new=transport):
                reservation=live.reserve(1,32000)[0]
                args=([{'role':'system','content':'Trusted'},{'role':'developer','content':'Separation'},
                       {'role':'user','content':'EXPLICIT SYNTHETIC TEST'}],Answer.model_json_schema(),'generation',reservation)
                if status in (401,307):
                    with self.assertRaises(live.ModelFailure) as caught:
                        live.call(*args)
                    self.assertEqual(caught.exception.category,'authentication_or_permission' if status==401 else 'provider_or_schema_error')
                    self.assertEqual(caught.exception.record['http_status'],status)
                    self.assertEqual(caught.exception.record['exception_type'],'AuthenticationError' if status==401 else 'APIStatusError')
                    self.assertIsNone(caught.exception.record['usage'])
                    self.assertEqual(caught.exception.record['attempts'],1)
                    with reg.connect() as db:
                        row=db.execute('SELECT status,data FROM calls WHERE id=?',(reservation,)).fetchone()
                    self.assertEqual(row['status'],'failed')
                    self.assertEqual(json.loads(row['data'])['reservation'],32000)
                else:
                    raw,record=live.call(*args)
                    Answer.model_validate_json(raw)
                    self.assertEqual(record['usage']['total_tokens'],10)
            self.assertEqual(len(observed),1,'No retry is permitted')
            record = caught.exception.record if status in (401,307) else record
            self.assertEqual(record['destination'], {'scheme':'https','host':'api.groq.com','path':'/openai/v1/chat/completions'})
            self.assertEqual(record['provider_request_id'],'req_synthetic_401' if status==401 else None)
            self.assertIn('finished_at',record)
            self.assertTrue(record['single_bearer_matches_effective_credential'])
            return record

    def test_actual_sdk_assembles_correct_endpoint_and_explicit_credential(self):
        self.exercise(200)

    def test_synthetic_401_classified_once_and_reservation_retained(self):
        self.exercise(401)

    def test_redirect_is_not_followed(self):
        self.exercise(307)


if __name__=='__main__':
    unittest.main()
