"""Offline Phase 6 preparation checks. Explicit dummy approvals/cases only."""
import hashlib
import json
import sqlite3
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from app.core.config import LiveSettings
from app.evaluation import experiment as exp
from app.llm.client import Approval
from scripts import prepare_phase6 as prep


class FakeClock:
    def __init__(self):
        self.value=0.0
        self.sleeps=[]

    def now(self):
        return self.value

    def sleep(self, seconds):
        self.sleeps.append(seconds)
        self.value+=seconds


class Phase6PreparationTests(unittest.TestCase):
    def setUp(self):
        for name in ('socket.socket.connect','socket.create_connection'):
            p=patch(name, side_effect=AssertionError('Provider/network forbidden'))
            p.start(); self.addCleanup(p.stop)

    def test_offline_preparation_rejects_live_flags_before_reading_or_calling(self):
        for free_only, enabled in ((False,False),(True,True)):
            with patch.object(prep.LiveSettings, 'from_env', return_value=LiveSettings(free_only,enabled,'TEST ONLY','TEST ONLY')), \
                 patch.object(prep.live,'call') as call, patch.object(prep.live,'reserve') as reserve:
                with self.assertRaisesRegex(ValueError,'Offline preparation requires'):
                    prep.prepare()
                call.assert_not_called(); reserve.assert_not_called()

    def test_single_benign_plan_uses_existing_four_call_128000_reservation(self):
        case={'case_id':prep.CASE_ID,'split':'development'}
        with patch.object(exp,'load',return_value={'cases':[case]}):
            plan=exp.plan('development',1,case_id=prep.CASE_ID)
        self.assertEqual(plan['case_attempts'],3)
        self.assertEqual(plan['maximum_api_calls_without_retries'],4)
        self.assertEqual(plan['conservative_reserved_tokens'],128000)

    def test_allowance_accounting_is_read_only_and_counts_reserved_unknown_calls(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            a=Approval(provider='groq',allowance_id='EXPLICIT-TEST',confirmed_free_promotional=False,
                       approved_model='TEST ONLY',expires_at=datetime.now(timezone.utc)+timedelta(hours=1),
                       max_calls=4,max_reserved_tokens=160000,chat_completions_supported=True,
                       structured_outputs_supported=True,max_output_tokens_supported=True,
                       confirmation_note='EXPLICIT TEST ONLY; no approval claim')
            path=root/'approval.json';path.write_text(a.model_dump_json())
            dbpath=root/'registry.sqlite3'
            with sqlite3.connect(dbpath) as db:
                db.execute('CREATE TABLE calls(allowance_id TEXT,data TEXT)')
                db.executemany('INSERT INTO calls VALUES(?,?)',[
                    (a.allowance_id,json.dumps({'reservation':32000,'status':'reserved'})),
                    (a.allowance_id,json.dumps({'reservation':32000,'status':'unknown'})),
                    ('OTHER',json.dumps({'reservation':99999}))])
            before={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in root.iterdir()}
            with patch.object(prep,'settings',SimpleNamespace(app_data_directory=root)):
                result=prep.accounting(LiveSettings(True,False,'TEST ONLY','TEST ONLY',path))
            self.assertEqual(result['remaining_calls'],2)
            self.assertEqual(result['remaining_reserved_tokens'],96000)
            self.assertEqual(result['reserved_call_records'],2)
            self.assertEqual({p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in root.iterdir()},before)


class Phase6RunnerTests(unittest.TestCase):
    """EXPLICIT SYNTHETIC answers/screens/approval settings; transport forbidden."""
    def setUp(self):
        from scripts import phase6_smoke
        self.runner=phase6_smoke
        self.clock=FakeClock()
        pacer_type=phase6_smoke.RequestPacer
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.initial={'hits':[{'id':'TEST-SOURCE','text':'EXPLICIT SYNTHETIC TEST ONLY: Friday.'}],
                      'snapshot':[],'omitted_ids':[]}
        self.prepared={'case_id':prep.CASE_ID,'run_id':prep.RUN_ID,'protocol':'paired',
            'identity':{'test_only':True},'readiness':{'local_approval_checks_pass':True},
            'initial_retrieved_evidence':self.initial,'local_budget':{'approval_fingerprint':'TEST ONLY'},
            'workload':{'maximum_api_calls_without_retries':4,'conservative_reserved_tokens':128000,'case_attempts':3}}
        from app.storage import registry
        from app.rag import assistant
        self.assistant=assistant
        fixtures=[patch.object(registry,'ROOT',self.root),
            patch.object(self.runner,'RequestPacer',side_effect=lambda: pacer_type(self.clock.now,self.clock.sleep)),
            patch.object(self.runner.LiveSettings,'from_env',return_value=LiveSettings(True,True,'TEST ONLY','TEST ONLY')),
            patch.object(prep,'prepare',return_value=self.prepared),
            patch.object(prep,'accounting',return_value={'TEST ONLY':True}),
            patch.object(exp,'search',return_value=self.initial),
            patch('socket.socket.connect',side_effect=AssertionError('Network forbidden')),
            patch('socket.create_connection',side_effect=AssertionError('Network forbidden'))]
        for p in fixtures:
            p.start();self.addCleanup(p.stop)

    def diagnostic(self):
        return json.loads((self.root/'experiments'/prep.RUN_ID/'integration-diagnostics.json').read_text())

    def drive(self, bad_screen=False):
        def call(messages,schema,stage,reservation):
            raw=({'unexpected':'EXPLICIT SYNTHETIC INVALID SCREEN'} if bad_screen else
                 {'question_flagged':False,'flagged_source_ids':[],'reason_codes':['none']}) if stage=='screening' else {
                 'status':'answered','answer':'EXPLICIT SYNTHETIC TEST ONLY: Friday.','source_ids':['TEST-SOURCE']}
            return json.dumps(raw), {'stage':stage,'usage':None,'provider_request_id':None}
        def run(*args,**kwargs):
            self.assertEqual(args,(prep.RUN_ID,'development','paired',1,5,True))
            self.assertEqual(kwargs,{'case_id':prep.CASE_ID})
            for mode in 'ABC':
                r=self.assistant.respond('EXPLICIT TEST QUESTION',mode,initial=self.initial)
                if r['status'] not in exp.COMPLETED:
                    from app.llm.client import LiveBlocked
                    raise LiveBlocked('EXPLICIT synthetic operational failure')
        with patch.object(self.runner.live,'call',side_effect=call), \
             patch.object(self.runner.live,'reserve',side_effect=lambda n,t,metadata=None:['TEST-RESERVATION']*n), \
             patch.object(self.runner.live,'validate_interactive_input'), \
             patch.object(self.runner.live,'stop_paid_test_on_error'), \
             patch.object(exp,'run',side_effect=run):
            self.runner.execute(self.prepared)

    def test_synthetic_four_calls_captured_no_retries_and_no_resume(self):
        from app.llm.client import LiveBlocked
        self.drive()
        d=self.diagnostic()
        self.assertEqual((d['reserved_calls'],d['reserved_tokens']),(4,128000))
        self.assertEqual([a['stage'] for a in d['attempts']],['generation','generation','screening','generation'])
        self.assertTrue(all(a['schema_valid'] for a in d['attempts']))
        self.assertTrue(all(a['usage'] is None for a in d['attempts']))
        self.assertEqual([a['boundary_started_monotonic'] for a in d['attempts']],[0,65,130,195])
        self.assertEqual([a['pacing_wait_seconds'] for a in d['attempts']],[0,65,65,65])
        self.assertEqual(d['attempts'][3]['boundary_started_monotonic']-d['attempts'][2]['boundary_started_monotonic'],65)
        with self.assertRaisesRegex(LiveBlocked,'cannot be resumed'):
            self.runner.execute(self.prepared)

    def test_synthetic_invalid_screen_recorded_and_no_repair(self):
        from app.llm.client import LiveBlocked
        with self.assertRaises(LiveBlocked):
            self.drive(bad_screen=True)
        d=self.diagnostic()
        self.assertEqual(len(d['attempts']),3)
        self.assertFalse(d['attempts'][-1]['schema_valid'])
        self.assertEqual(d['outcome'],'stopped_or_interrupted_no_automatic_retry')

    def test_unconfirmed_readiness_refuses_before_call_or_result_creation(self):
        from app.llm.client import LiveBlocked
        self.prepared['readiness']['local_approval_checks_pass']=False
        with self.assertRaisesRegex(LiveBlocked,'fresh passing readiness'):
            self.runner.execute(self.prepared)
        self.assertFalse((self.root/'experiments').exists())

    def test_reservation_ceiling_rejects_before_underlying_reserve(self):
        from app.llm.client import LiveBlocked
        def runaway(*args,**kwargs):
            self.runner.live.reserve(5,160000)
        with patch.object(self.runner.live,'reserve') as reserve,patch.object(exp,'run',side_effect=runaway):
            with self.assertRaisesRegex(LiveBlocked,'reservation ceiling'):
                self.runner.execute(self.prepared)
            reserve.assert_not_called()

    def test_synthetic_provider_failure_preserves_unknown_usage_without_retry(self):
        from app.llm.client import ModelFailure
        def failed(*args,**kwargs):
            raise ModelFailure('timeout_usage_unknown',{'usage':None,'provider_request_id':None,'attempts':1})
        def run(*args,**kwargs):
            self.runner.live.call([],{},'generation','TEST-RESERVATION')
        with patch.object(self.runner.live,'call',side_effect=failed) as provider,patch.object(exp,'run',side_effect=run):
            with self.assertRaises(ModelFailure):
                self.runner.execute(self.prepared)
            self.assertEqual(provider.call_count,1)
        row=self.diagnostic()['attempts'][0]
        self.assertEqual(row['outcome'],'timeout_usage_unknown')
        self.assertIsNone(row['usage']);self.assertIsNone(row['response'])

    def test_fifth_synthetic_request_refused_before_transport(self):
        from app.llm.client import LiveBlocked
        def run(*args,**kwargs):
            for _ in range(5):
                self.runner.live.call([],{},'generation','TEST-RESERVATION')
        raw=json.dumps({'status':'answered','answer':'EXPLICIT TEST ONLY','source_ids':['TEST-SOURCE']})
        with patch.object(self.runner.live,'call',return_value=(raw,{'usage':None})) as provider,patch.object(exp,'run',side_effect=run):
            with self.assertRaisesRegex(LiveBlocked,'request ceiling'):
                self.runner.execute(self.prepared)
            self.assertEqual(provider.call_count,4)
        self.assertEqual(len(self.diagnostic()['attempts']),4)


class RequestPacerTests(unittest.TestCase):
    def test_variable_setup_and_transport_delays_keep_actual_starts_apart(self):
        from scripts.phase6_smoke import RequestPacer
        clock=FakeClock()
        pacer=RequestPacer(clock.now,clock.sleep)
        starts=[]
        for setup, duration in [(50,2),(0,5),(90,1),(0,3)]:
            pacer.wait()
            clock.value+=setup
            starts.append(clock.now())  # Simulated actual transport start.
            clock.value+=duration
            pacer.finished()
        self.assertTrue(all(b-a>=65 for a,b in zip(starts,starts[1:])))
        self.assertEqual(starts,[50,117,277,343])

    def test_early_waking_sleep_rechecks_deadline_and_elapsed_time_counts(self):
        from scripts.phase6_smoke import RequestPacer
        clock=FakeClock()
        def short_sleep(seconds):
            clock.value+=min(seconds,10)
        pacer=RequestPacer(clock.now,short_sleep)
        pacer.finished()
        self.assertEqual(pacer.wait(),65)
        pacer.finished()
        clock.value+=70
        self.assertEqual(pacer.wait(),0)

    def test_interrupted_wait_does_not_reach_next_provider_boundary(self):
        from scripts.phase6_smoke import RequestPacer
        clock=FakeClock()
        def interrupted(seconds):
            raise KeyboardInterrupt()
        pacer=RequestPacer(clock.now,interrupted)
        pacer.finished()
        with self.assertRaises(KeyboardInterrupt):
            pacer.wait()
        self.assertEqual(clock.now(),0)


if __name__=='__main__':
    unittest.main()
