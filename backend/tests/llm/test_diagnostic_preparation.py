"""Synthetic diagnostics only: socket-blocked adapter, no ledger or provider."""
import unittest,json
from unittest.mock import patch
from types import SimpleNamespace
import httpx
from app.llm.azure_openai import generate,AzureStatusError
from app.llm.diagnostics import error_details

class DiagnosticPreparationTests(unittest.TestCase):
    def exercise(self,body):
        observed=[]
        def handler(_transport,request):
            observed.append(True)
            return httpx.Response(400,request=request,json={'error':body},headers={'apim-request-id':'synthetic-diag-01'})
        config=SimpleNamespace(provider='azure_openai',model='synthetic',request_timeout_seconds=30,base_url='https://synthetic.openai.azure.com/openai/v1',api_key='SYNTHETIC-PRIVATE-CREDENTIAL')
        with patch('socket.socket.connect',side_effect=AssertionError('Blocked')),patch('socket.create_connection',side_effect=AssertionError('Blocked')),patch.object(httpx.HTTPTransport,'handle_request',new=handler):
            with self.assertRaises(AzureStatusError) as capture:
                generate([SimpleNamespace(type='system',content='Synthetic')],{'title':'Synthetic','type':'object'},config,lambda r:None,lambda r:None)
        result=error_details(capture.exception,config.api_key)
        self.assertEqual(capture.exception.status_code,400)
        self.assertEqual(result['provider_request_id'],'synthetic-diag-01')
        self.assertEqual(len(observed),1)
        self.assertNotIn(config.api_key,json.dumps(result))
        self.assertLessEqual(len(result.get('provider_error_message') or ''),512)
        return result

    def test_parameter_code_type_and_bounded_explanation(self):
        r=self.exercise({'code':'unsupported_parameter','type':'invalid_request_error','param':'temperature','message':'Invalid request '+('SYNTHETIC-PRIVATE-CREDENTIAL '*100)})
        self.assertEqual(r['provider_error_code'],'unsupported_parameter')
        self.assertEqual(r['provider_error_type'],'invalid_request_error')
        self.assertEqual(r['provider_error_parameter'],'temperature')

    def test_safe_nested_content_categories(self):
        r=self.exercise({'code':'content_filter','innererror':{'code':'ResponsibleAIPolicyViolation','content_filter_result':{'jailbreak':{'filtered':True},'hate':{'filtered':False},'sexual':{'filtered':'true'},'SYNTHETIC-PRIVATE-CREDENTIAL':{'filtered':True}}}})
        self.assertEqual(r['provider_inner_error_code'],'ResponsibleAIPolicyViolation')
        self.assertEqual(r['provider_content_filter_categories'],['jailbreak'])

    def test_unknown_fields_never_dumped_or_inferred_from_400(self):
        r=self.exercise({'param':'SYNTHETIC-PRIVATE-CREDENTIAL','code':'unknown-echo','message':'SYNTHETIC-PRIVATE-CREDENTIAL','innererror':{'code':'unknown-echo','private':'SYNTHETIC-PRIVATE-CREDENTIAL'}})
        self.assertEqual(r['provider_error_parameter'],'[REDACTED]')
        self.assertEqual(r['provider_error_code'],'[REDACTED]')
        self.assertIsNone(r['provider_content_filter_categories'])
        self.assertIn('may be insufficient',r['diagnostic_detail_policy'])
