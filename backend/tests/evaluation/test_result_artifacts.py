import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from fastapi import HTTPException
from app.api import runtime
from app.llm import diagnostics
from frontend.error_messages import describe_error

class ResultArtifactTests(unittest.TestCase):
    def test_export_allowlist_missing_files_and_symlinks(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(runtime.reg,'ROOT',Path(tmp)):
            folder=Path(tmp)/'experiments'/'actual';folder.mkdir(parents=True)
            (folder/'experiment.json').write_text('{}');(folder/'records.csv').write_text('status\nanswered\n')
            self.assertEqual(runtime.result_artifact('actual','records.csv').media_type,'text/csv')
            (folder/'records.json').symlink_to(folder/'experiment.json')
            for run,name in [('..','records.csv'),('actual','experiment.json'),('actual','asr.png'),('actual','records.json')]:
                with self.subTest(run=run,name=name),self.assertRaises(HTTPException):runtime.result_artifact(run,name)

    def test_allowlisted_content_policy_codes_no_nested_echo(self):
        for code in ['content_filter','ResponsibleAIPolicyViolation','content_policy_violation','SYNTHETIC-PRIVATE-KEY']:
            exc=SimpleNamespace(body={'error':{'code':code,'message':'SYNTHETIC-PRIVATE-KEY','innererror':{'secret':'SYNTHETIC-PRIVATE-KEY'}}},response=None,__cause__=None,__context__=None)
            result=diagnostics.error_details(exc,'SYNTHETIC-PRIVATE-KEY')
            self.assertNotIn('SYNTHETIC-PRIVATE-KEY',str(result))
            self.assertEqual(result['provider_error_code'],code if code!='SYNTHETIC-PRIVATE-KEY' else '[REDACTED]')

    def test_error_explanations_do_not_infer_defense_success(self):
        for code in [None,'content_filter']:
            message=describe_error({'calls':[{'http_status':400,'provider_error_code':code}]})
            self.assertIn('not',message)
        self.assertIn('quota',describe_error({'calls':[{'http_status':429}]}))
