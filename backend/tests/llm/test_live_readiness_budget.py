"""Read-only budget readiness and UI submit controls; no provider requests."""
from datetime import datetime,timedelta,timezone
from backend.tests.offline_settings import offline_environment
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import httpx
from streamlit.testing.v1 import AppTest
from app.storage import registry as reg
from app.llm import client as live
from frontend.error_messages import describe_error


class ReadinessTests(unittest.TestCase):
    def setUp(self):
        guard=offline_environment();guard.start();self.addCleanup(guard.stop)

    def test_remaining_capacity_and_c_combined_budget(self):
        with tempfile.TemporaryDirectory() as folder,patch.object(reg,'ROOT',Path(folder)):
            reg.initialize()
            a=live.Approval(provider='nvidia_nim',allowance_id='SYNTHETIC',confirmed_free_promotional=True,
                approved_model='test',expires_at=datetime.now(timezone.utc)+timedelta(hours=1),max_calls=2,
                max_reserved_tokens=64000,chat_completions_supported=True,structured_outputs_supported=True,
                max_output_tokens_supported=True,confirmation_note='Synthetic only')
            with patch.object(live,'approval',return_value=a),patch('socket.socket.connect',side_effect=AssertionError('No network')):
                self.assertTrue(live.readiness()['mode_available']['C'])
                with reg.connect() as db:
                    db.execute('INSERT INTO calls VALUES(?,?,?,?,?)',('one',a.allowance_id,'generation','failed',json.dumps({'reservation':32000})))
                status=live.readiness()
                self.assertTrue(status['enabled']);self.assertTrue(status['mode_available']['B'])
                self.assertFalse(status['mode_available']['C'])
                with reg.connect() as db:
                    db.execute('INSERT INTO calls VALUES(?,?,?,?,?)',('two',a.allowance_id,'generation','failed',json.dumps({'reservation':32000})))
                    before=[tuple(r) for r in db.execute('SELECT * FROM calls ORDER BY id')]
                status=live.readiness()
                self.assertFalse(status['enabled']);self.assertEqual(status['remaining_calls'],0)
                self.assertIn('exhausted',status['reason'])
                with reg.connect() as db:self.assertEqual(before,[tuple(r) for r in db.execute('SELECT * FROM calls ORDER BY id')])

    def test_ui_disables_unfunded_modes_without_submission(self):
        budget={'enabled':True,'remaining_calls':1,'remaining_reserved_tokens':32000,
                'expires_at':'synthetic-expiry','mode_available':{'A':True,'B':True,'C':False}}
        seen=[]
        def request(method,url,**kwargs):
            self.assertEqual(method,'GET');seen.append(url)
            data={'live':budget,'limits':{}} if url.endswith('/ready') else {'documents':[],'runs':[]}
            return httpx.Response(200,json=data,request=httpx.Request(method,url))
        with patch('httpx.request',side_effect=request),patch('socket.socket.connect',side_effect=AssertionError('No network')):
            app=AppTest.from_file(str(Path('frontend/streamlit_app.py').resolve())).run()
            self.assertFalse(app.exception)
            ask=lambda:next(button for button in app.button if button.label=='Ask once')
            self.assertFalse(ask().disabled)
            app.selectbox[0].set_value('C').run()
            self.assertTrue(ask().disabled)
            app.selectbox[0].set_value('A').run()
            self.assertFalse(ask().disabled)
            budget.update(enabled=False,remaining_calls=0,remaining_reserved_tokens=0,
                reason='Local allowance exhausted',mode_available={'A':False,'B':False,'C':False})
            app.run();self.assertTrue(ask().disabled)
            self.assertTrue(any('exhausted' in item.value for item in app.warning))
        self.assertTrue(all('/chat' not in url for url in seen))

    def test_timeout_message_is_actionable(self):
        self.assertIn('request timeout',describe_error({'calls':[{'error':'timeout_usage_unknown'}]}))
