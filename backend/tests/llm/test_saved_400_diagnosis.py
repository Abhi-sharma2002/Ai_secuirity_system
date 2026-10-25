"""Adapter error-retention checks with synthetic HTTP and blocked sockets only."""
import unittest
from types import SimpleNamespace
from unittest.mock import patch
import httpx
from app.llm.azure_openai import generate,AzureStatusError
from app.llm.diagnostics import error_details

class Saved400DiagnosisTests(unittest.TestCase):
    def exercise(self,code=None,nonjson=False):
        requests=[]
        def handler(_transport,request):
            requests.append(request)
            return httpx.Response(400,request=request,headers={'apim-request-id':'offline-request-400'},
                **({'text':'SYNTHETIC-PRIVATE-KEY'} if nonjson else {'json':{'error':{'code':code,'message':'SYNTHETIC-PRIVATE-KEY','innererror':{'private':'SYNTHETIC-PRIVATE-KEY'}}}}))
        config=SimpleNamespace(provider='azure_openai',model='offline-deployment',request_timeout_seconds=30,
            base_url='https://offline.openai.azure.com/openai/v1',api_key='SYNTHETIC-PRIVATE-KEY')
        with patch('socket.socket.connect',side_effect=AssertionError('Network forbidden')),patch('socket.create_connection',side_effect=AssertionError('Network forbidden')),patch.object(httpx.HTTPTransport,'handle_request',new=handler):
            with self.assertRaises(AzureStatusError) as raised:
                generate([SimpleNamespace(type='system',content='Synthetic prompt')],{'title':'Synthetic','type':'object'},config,lambda r:None,lambda r:None)
        exc=raised.exception
        self.assertEqual(len(requests),1)
        self.assertEqual(exc.status_code,400)
        self.assertEqual(exc.body is None,nonjson)
        result=error_details(exc,config.api_key)
        self.assertEqual(result['provider_request_id'],'offline-request-400')
        self.assertNotIn(config.api_key,str(result))
        self.assertNotIn('innererror',result)
        return result

    def test_known_code_and_request_id_survive_safely(self):
        self.assertEqual(self.exercise('content_filter')['provider_error_code'],'content_filter')

    def test_unknown_machine_string_is_not_inferred(self):
        self.assertEqual(self.exercise('SYNTHETIC-UNKNOWN-OR-SECRET')['provider_error_code'],'[REDACTED]')

    def test_nonjson_body_retains_status_and_id_only(self):
        result=self.exercise(nonjson=True)
        self.assertIsNone(result['provider_error_code'])
        self.assertIsNone(result['provider_error_message'])
