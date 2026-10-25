import unittest,tempfile,json
from pathlib import Path
from unittest.mock import patch
from app.evaluation.provider_outcomes import provider_counts
from app.api import runtime
from fastapi import HTTPException
class ProviderOutcomesTests(unittest.TestCase):
    def test_filter_and_unknown400_are_not_conflated(self):
        rows=[{'response':{'calls':[{'http_status':400}]}},
              {'response':{'calls':[{'http_status':400,'provider_error_code':'content_filter'}]}}]
        r=provider_counts(rows)
        self.assertEqual(r['confirmed_filter_calls'],1)
        self.assertEqual(r['unclassified_http400_calls'],1)
        self.assertNotIn('attack_success',r)
    def test_diagnostic_read_is_separate_and_allowlisted(self):
        with tempfile.TemporaryDirectory() as tmp,patch.object(runtime.reg,'ROOT',Path(tmp)):
            p=Path(tmp)/'diagnostics'/'sample';p.mkdir(parents=True)
            (p/'operational-summary.json').write_text(json.dumps({'outcome':'llm_error','binding':'PRIVATE TEST VALUE'}))
            self.assertEqual(runtime.diagnostics_list()['diagnostics'],['sample'])
            r=runtime.diagnostic_summary('sample')
            self.assertNotIn('PRIVATE TEST VALUE',str(r))
            with self.assertRaises(HTTPException):runtime.diagnostic_summary('..')
