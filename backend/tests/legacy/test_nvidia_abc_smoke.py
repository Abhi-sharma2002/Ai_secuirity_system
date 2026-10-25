"""Historical NVIDIA paired runner: synthetic responses and fake pacing only."""
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch
from app.storage import registry as reg
from app.core.config import LiveSettings
from app.llm import client as live
from scripts.history import nvidia_abc_smoke as smoke
from scripts.phase6_smoke import RequestPacer


class SmokeTests(unittest.TestCase):
    def exercise(self,failure=None):
        now=[0.0];seen=[];reserved=[]
        pacer=RequestPacer(clock=lambda:now[0],sleep=lambda delay:now.__setitem__(0,now[0]+delay))
        initial={'hits':[{'id':'source','text':'Mentor check-ins every Friday.'}],'snapshot':[],'omitted_ids':[]}
        data={'cases':[{'case_id':'development-02','split':'development','query':'When?',
                        'fixtures':['fixture'],'channel':'indirect','adversarial':False}]}
        snap={'items':{'fixture':{'id':'test-version','document_id':'test-document'}}}
        c=LiveSettings(True,False,'synthetic','nvidia/nemotron-3.5-super-vl-120b-a12b',provider='nvidia_nim',
                       base_url='https://integrate.api.nvidia.com/v1')
        def reserve(calls,tokens,metadata):
            reserved.append((calls,tokens));return [f'{len(reserved)}-{i}' for i in range(calls)]
        def call(messages,schema,stage,reservation):
            seen.append((stage,now[0]))
            if failure=='provider':raise live.ModelFailure('synthetic_provider_error',{'usage':None})
            output=({'question_flagged':False,'flagged_source_ids':[],'reason_codes':['none']}
                    if stage=='screening' else {'status':'answered','answer':'SYNTHETIC ONLY','source_ids':['source']})
            if stage=='screening' and failure=='schema':output={'invalid':'synthetic'}
            return json.dumps(output),{'stage':stage,'usage':None}
        with tempfile.TemporaryDirectory() as folder,patch.object(reg,'ROOT',Path(folder)):
            output=Path(folder)/'experiments'/smoke.RUN_ID;output.mkdir(parents=True)
            d={'attempts':[],'reserved_calls':0,'reserved_tokens':0}
            approval=SimpleNamespace(provider='nvidia_nim',approved_model=c.model,max_calls=5,max_reserved_tokens=160000)
            with patch('socket.socket.connect',side_effect=AssertionError('Network forbidden')), \
                 patch('socket.create_connection',side_effect=AssertionError('Network forbidden')), \
                 patch.object(smoke,'RequestPacer',return_value=pacer), \
                 patch.object(smoke,'public_accounting',return_value={'synthetic_accounting':True}), \
                 patch.object(live,'reserve',side_effect=reserve),patch.object(live,'call',side_effect=call), \
                 patch.object(live,'validate_interactive_input'),patch.object(live,'stop_paid_test_on_error'), \
                 patch.object(smoke.exp,'approval',return_value=approval),patch.object(smoke.exp,'report'), \
                 patch.object(smoke.exp,'git_state',return_value={'revision':'synthetic','dirty':True}), \
                 patch.object(LiveSettings,'from_env',return_value=c),redirect_stdout(io.StringIO()):
                if failure:
                    with self.assertRaises(live.LiveBlocked):smoke.run_bounded(output,data,snap,initial,c,d)
                else:smoke.run_bounded(output,data,snap,initial,c,d)
            if not failure:
                self.assertEqual(seen,[('generation',0),('generation',65),('screening',130),('generation',195)])
                self.assertEqual(reserved,[(1,32000),(1,32000),(2,64000)])
                self.assertEqual((d['reserved_calls'],d['reserved_tokens']),(4,128000))
                self.assertTrue(all(row['schema_valid'] for row in d['attempts']))
            elif failure=='provider':
                self.assertEqual(len(seen),1);self.assertEqual(reserved,[(1,32000)])
            else:
                self.assertEqual(len(seen),3);self.assertFalse(d['attempts'][-1]['schema_valid'])
                self.assertEqual(d['reserved_tokens'],128000)
            self.assertEqual(len(seen),len(d['attempts']))

    def test_four_attempts_and_completion_based_pacing(self):self.exercise()
    def test_operational_error_stops_immediately(self):self.exercise('provider')
    def test_invalid_screen_stops_without_generation_or_repair(self):self.exercise('schema')
