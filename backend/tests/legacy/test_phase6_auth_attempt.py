"""Offline single-attempt guard verification; no real ledger/provider access."""
import json
import unittest
from unittest.mock import patch
from scripts.history import phase6_auth_attempt as run


class BoundTests(unittest.TestCase):
    def test_actual_assistant_success_and_failure_each_call_once(self):
        prepared=json.loads(run.PREPARED.read_text())
        source=prepared['initial_retrieved_evidence']['hits'][0]['id']
        for fail in (False,True):
            diagnostic={'reserved_calls':0,'attempts':[]}
            record={'usage':None,'provider_request_id':None}
            with patch('socket.socket.connect',side_effect=AssertionError('Network forbidden')), \
                 patch.object(run.live,'reserve',return_value=['new']) as reserve, \
                 patch.object(run.live,'call') as call:
                if fail: call.side_effect=run.live.ModelFailure('authentication_or_permission',record)
                else: call.return_value=(json.dumps({'status':'answered','answer':'Friday','source_ids':[source]}),record)
                result=run.bounded_response(prepared,diagnostic,lambda:None)
                self.assertEqual(reserve.call_count,1)
                self.assertEqual(reserve.call_args.args[:2],(1,32000))
                self.assertEqual(call.call_count,1)
                self.assertEqual(len(diagnostic['attempts']),1)
                self.assertEqual(result['status'],'llm_error' if fail else 'answered')

    def test_repeated_boundary_and_reservation_are_blocked(self):
        prepared=json.loads(run.PREPARED.read_text())
        diagnostic={'reserved_calls':0,'attempts':[]}
        def adversarial_respond(*args,**kwargs):
            ids=run.live.reserve(1,32000)
            with self.assertRaises(run.live.LiveBlocked): run.live.reserve(1,32000)
            run.live.call([],{},'generation',ids[0])
            with self.assertRaises(run.live.LiveBlocked): run.live.call([],{},'generation',ids[0])
            return {}
        with patch('socket.socket.connect',side_effect=AssertionError('Network forbidden')), \
             patch.object(run.live,'reserve',return_value=['new']) as reserve, \
             patch.object(run.live,'call',return_value=('{}',{})) as call, \
             patch.object(run.assistant,'respond',side_effect=adversarial_respond):
            run.bounded_response(prepared,diagnostic,lambda:None)
            self.assertEqual(reserve.call_count,1)
            self.assertEqual(call.call_count,1)
