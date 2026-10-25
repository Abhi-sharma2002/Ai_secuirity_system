"""Azure wire/gate/control-flow checks. Synthetic responses, temporary ledgers only."""
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import httpx

from app.core.config import LiveSettings
from app.storage import registry as reg
from app.llm import client as live
from app.rag import assistant
from app.evaluation import experiment as exp
from scripts import azure_live_integration as integration

BASE = 'https://synthetic-resource.openai.azure.com/openai/v1'
ENV = {'LLM_BACKEND': 'azure_openai', 'AZURE_OPENAI_API_KEY': 'SYNTHETIC-PRIVATE-KEY',
       'AZURE_OPENAI_ENDPOINT': BASE, 'AZURE_OPENAI_DEPLOYMENT': 'actual-test-deployment',
       'FREE_ONLY': 'true', 'LIVE_LLM_ENABLED': 'true', 'LLM_REQUEST_TIMEOUT_SECONDS': '30'}
CLEAR = {'question_flagged': False, 'flagged_source_ids': [], 'reason_codes': ['none']}
INITIAL = {'hits': [{'id': 'source-1', 'text': 'Mentor check-ins occur every Friday.',
                    'filename': 'fictional.md', 'version_id': 'v1', 'document_id': 'd1',
                    'page': 0, 'section': 'text', 'partial_text': False}],
           'snapshot': [], 'omitted_ids': []}
ANSWER = {'status': 'answered', 'answer': 'Mentor check-ins occur every Friday.', 'source_ids': ['source-1']}


def approval_values():
    now = datetime.now(timezone.utc)
    return dict(provider='azure_openai', allowance_id='SYNTHETIC-AZURE-ONLY',
        confirmed_free_promotional=True, approved_model=ENV['AZURE_OPENAI_DEPLOYMENT'],
        approved_endpoint=BASE, deployment_model_version='synthetic-model/version',
        expires_at=now+timedelta(hours=1), activated_at=now, max_calls=5, max_reserved_tokens=160000,
        chat_completions_supported=True, structured_outputs_supported=True, max_output_tokens_supported=True,
        confirmation_note='SYNTHETIC TEST FIXTURE; not actual operator account evidence',
        entitlement_expiry='unknown', eligibility_evidence='Synthetic test eligibility and sufficient quota only',
        eligibility_checked_at=now)


class AzureTests(unittest.TestCase):
    @contextmanager
    def session(self, *, status=200, screen=CLEAR, answer=ANSWER, timeout=False, capacity=5):
        observed = []
        def transport(_transport, request):
            observed.append(request)
            if timeout:
                raise httpx.ReadTimeout('synthetic timeout', request=request)
            body = json.loads(request.content)
            result = screen if body['response_format']['json_schema']['name'] == 'Screening' else answer
            content = result if isinstance(result, str) else json.dumps(result)
            return httpx.Response(status, request=request, headers={'apim-request-id': 'synthetic-request-1'},
                json={'id': 'synthetic-response', 'choices': [{'message': {'content': content}, 'finish_reason': 'stop'}],
                      'usage': {'prompt_tokens': 8, 'completion_tokens': 4, 'total_tokens': 12},
                      'error': {'code': 'invalid_api_key', 'message': 'Invalid API key '+ENV['AZURE_OPENAI_API_KEY']}})
        with tempfile.TemporaryDirectory() as folder, patch.object(reg, 'ROOT', Path(folder)), \
             patch.dict(os.environ, ENV|{'AZURE_OPENAI_ALLOWANCE_FILE': str(Path(folder)/'approval.json')}, clear=True), \
             patch('socket.socket.connect', side_effect=AssertionError('No network')), \
             patch('socket.create_connection', side_effect=AssertionError('No network')), \
             patch.object(httpx.HTTPTransport, 'handle_request', new=transport):
            reg.initialize()
            a = live.Approval(**(approval_values()|{'max_calls': capacity, 'max_reserved_tokens': capacity*32000}))
            path = LiveSettings.from_env().allowance_file
            path.write_text(a.model_dump_json())
            yield observed, a, path

    def test_v1_payload_auth_roles_and_paired_settings(self):
        with self.session() as (observed, _, _):
            results = [assistant.respond('When are mentor check-ins?', mode, initial=INITIAL) for mode in 'ABC']
            self.assertEqual([r['status'] for r in results], ['answered']*3)
            self.assertEqual(len(observed), 4)
            payloads = [json.loads(r.content) for r in observed]
            for request, payload in zip(observed, payloads):
                self.assertEqual(str(request.url), BASE+'/chat/completions')
                self.assertEqual(request.headers.get_list('api-key'), [ENV['AZURE_OPENAI_API_KEY']])
                self.assertNotIn('authorization', request.headers)
                self.assertEqual((payload['model'], payload['max_completion_tokens']),
                                 (ENV['AZURE_OPENAI_DEPLOYMENT'], 700))
                self.assertNotIn('temperature', payload)
                self.assertNotIn('seed', payload)
                self.assertNotIn('max_tokens', payload)
                self.assertNotIn('tools', payload)
                self.assertTrue(payload['response_format']['json_schema']['strict'])
                self.assertTrue(all(t == 30 for t in request.extensions['timeout'].values()))
                self.assertEqual([m['role'] for m in payload['messages']], ['system', 'user'])
                self.assertEqual(json.loads(payload['messages'][1]['content'])['sources'], INITIAL['hits'])
            self.assertEqual(payloads[0]['messages'][0]['content'], assistant.GROUND)
            self.assertEqual(payloads[1]['messages'][0]['content'], assistant.GROUND+'\n\n'+assistant.SEPARATION)
            self.assertEqual(payloads[2]['messages'][0]['content'], assistant.SCREEN)
            self.assertEqual(payloads[1], payloads[3])
            self.assertEqual(results[2]['screening'], CLEAR)
            for result in results:
                for call in result['calls']:
                    self.assertEqual(call['settings']['temperature'], 'not sent')
                    self.assertEqual(call['settings']['provider_seed'], 'not sent')
                    self.assertEqual(call['settings']['configuration_version'],
                                     'azure-gpt5mini-v2-temperature-not-sent')
            self.assertEqual(results[2]['supplied_evidence'], INITIAL['hits'])
            self.assertEqual(results[2]['calls'][0]['usage']['total_tokens'], 12)
            self.assertEqual(results[0]['calls'][0]['provider_request_id'], 'synthetic-request-1')
            self.assertTrue(results[0]['calls'][0]['single_api_key_matches_effective_credential'])
            self.assertEqual(live.readiness()['remaining_calls'], 1)
            self.assertFalse(live.readiness()['mode_available']['C'])

    def test_error_once_no_retry_and_retained_usage(self):
        for status, category in ((401, 'authentication_or_permission'), (429, 'quota_or_rate_limit'),
                                 (500, 'provider_or_schema_error'), (307, 'provider_or_schema_error'),
                                 (202, 'provider_or_schema_error')):
            with self.subTest(status=status), self.session(status=status) as (observed, _, _):
                result = assistant.respond('Question?', 'A', initial=INITIAL)
                self.assertEqual(result['status'], 'llm_error')
                self.assertEqual(result['error'], category)
                self.assertEqual(len(observed), 1)
                self.assertEqual(result['reservation_units'], 32000)
                self.assertNotIn(ENV['AZURE_OPENAI_API_KEY'], json.dumps(result))
                self.assertIsNone(result['calls'][0]['usage'])
                if status == 429:
                    self.assertFalse(live.readiness()['enabled'])

    def test_timeout_usage_unknown_and_no_screen_fallback(self):
        with self.session(timeout=True) as (observed, _, _):
            result = assistant.respond('Question?', 'C', initial=INITIAL)
            self.assertEqual(result['status'], 'screening_error')
            self.assertEqual(result['error'], 'timeout_usage_unknown')
            self.assertEqual(len(observed), 1)
            self.assertEqual(result['reservation_units'], 64000)
            self.assertIsNone(result['calls'][0]['usage'])

    def test_bad_screen_and_citations_fail_closed(self):
        for screen in ('{"question_flagged":true,"question_flagged":false,"flagged_source_ids":[],"reason_codes":["none"]}',
                       CLEAR|{'flagged_source_ids': ['unknown']}, CLEAR|{'reason_codes': ['none','none']}):
            with self.subTest(screen=screen), self.session(screen=screen) as (observed, _, _):
                result = assistant.respond('Question?', 'C', initial=INITIAL)
                self.assertEqual(result['status'], 'screening_error')
                self.assertEqual(len(observed), 1)
        with self.session(answer=ANSWER|{'source_ids': ['invented']}) as (_, _, _):
            self.assertEqual(assistant.respond('Question?', 'A', initial=INITIAL)['status'], 'invalid_citations')

    def test_screen_removes_original_evidence_and_blocks_question(self):
        for decision, status in ((CLEAR|{'flagged_source_ids':['source-1']}, 'insufficient_evidence'),
                                 (CLEAR|{'question_flagged':True}, 'policy_blocked')):
            with self.subTest(decision=decision), self.session(screen=decision) as (observed, _, _):
                result = assistant.respond('Question?', 'C', initial=INITIAL)
                self.assertEqual(result['status'], status)
                self.assertEqual(result['candidate_evidence'], INITIAL['hits'])
                self.assertEqual(result['supplied_evidence'], [])
                self.assertEqual(len(observed), 1)

    def test_disabled_expired_and_insufficient_capacity_send_nothing(self):
        with self.session(capacity=1) as (observed, a, path):
            self.assertEqual(assistant.respond('Question?', 'C', initial=INITIAL)['status'], 'live_blocked')
            with patch.dict(os.environ, {'LIVE_LLM_ENABLED':'false'}):
                state = live.readiness()
                self.assertFalse(state['enabled'])
                self.assertEqual(state['remaining_calls'], 1)
                self.assertEqual(assistant.respond('Question?', 'A', initial=INITIAL)['status'], 'live_blocked')
            old = datetime.now(timezone.utc)-timedelta(hours=2)
            expired = a.model_dump()|{'activated_at':old,'eligibility_checked_at':old,'expires_at':old+timedelta(hours=1)}
            path.write_text(live.Approval(**expired).model_dump_json())
            self.assertFalse(live.readiness()['enabled'])
            self.assertEqual(assistant.respond('Question?', 'A', initial=INITIAL)['status'], 'live_blocked')
            self.assertEqual(observed, [])

    def test_azure_account_evidence_and_old_provider_approval_cannot_authorize(self):
        for changes in ({'confirmed_free_promotional':False,'entitlement_expiry':None},
                        {'approved_endpoint':'https://other.openai.azure.com/openai/v1'},
                        {'deployment_model_version':None}, {'entitlement_expiry':None},
                        {'provider':'nvidia_nim'}, {'provider':'groq'}):
            with self.subTest(changes=changes), self.session() as (observed, a, path):
                path.write_text(json.dumps(a.model_dump(mode='json')|changes))
                self.assertEqual(assistant.respond('Question?', 'A', initial=INITIAL)['status'], 'live_blocked')
                self.assertEqual(observed, [])

    def test_stop_survives_approval_edits(self):
        with self.session() as (observed, a, path):
            live.reserve(1,32000)
            fingerprint = hashlib.sha256(a.model_dump_json().encode()).hexdigest()
            with reg.connect() as db:
                db.execute('UPDATE allowance SET stopped=1 WHERE id=?', (fingerprint,))
            changed = a.model_copy(update={'confirmation_note':'Changed receipt, same allowance and prior stop'})
            path.write_text(changed.model_dump_json())
            self.assertTrue(live.readiness()['stopped'])
            with self.assertRaises(live.LiveBlocked):
                live.reserve(1,32000)
            self.assertEqual(observed, [])

    def test_stop_between_reservation_and_call_prevents_transport(self):
        with self.session() as (observed, a, _):
            reservation = live.reserve(1,32000)[0]
            with reg.connect() as db:
                db.execute('UPDATE allowance SET stopped=1')
            with self.assertRaises(live.LiveBlocked):
                live.call(assistant.messages('A','Question?',INITIAL['hits']),
                          assistant.Answer.model_json_schema(),'generation',reservation)
            self.assertEqual(observed, [])

    def test_azure_endpoint_validation_and_no_historical_routing(self):
        with patch.dict(os.environ, ENV, clear=True):
            for endpoint in ('https://synthetic-resource.openai.azure.com', BASE+'/', BASE+'/responses', BASE+'/chat/completions'):
                with patch.dict(os.environ, {'AZURE_OPENAI_ENDPOINT':endpoint}):
                    self.assertEqual(LiveSettings.from_env().base_url, BASE)
            for endpoint in ('http://x.openai.azure.com', 'https://key@x.openai.azure.com',
                             BASE+'?api-key=secret', BASE+'/other',
                             'https://api.groq.com/openai/v1', 'https://evil.openai.azure.com.example.com'):
                with patch.dict(os.environ, {'AZURE_OPENAI_ENDPOINT':endpoint}), self.assertRaises(ValueError):
                    LiveSettings.from_env()
            for provider in ('groq','nvidia_nim'):
                with patch.dict(os.environ, {'LLM_BACKEND':provider}), self.assertRaises(ValueError):
                    LiveSettings.from_env()

    def test_activation_requires_evidence_and_is_once_only(self):
        with self.session() as (observed, a, path):
            draft = a.model_dump(mode='json')|{'activated_at':None, 'expires_at':'2000-01-01T00:00:00Z'}
            path.write_text(json.dumps(draft|{'confirmed_free_promotional':False}))
            before = path.read_bytes()
            with self.assertRaises((ValueError,live.LiveBlocked)):
                integration.activate(LiveSettings.from_env())
            self.assertEqual(path.read_bytes(), before)
            path.write_text(json.dumps(draft))
            active = integration.activate(LiveSettings.from_env())
            self.assertEqual(active.expires_at-active.activated_at, timedelta(hours=1))
            with self.assertRaises(live.LiveBlocked):
                integration.activate(LiveSettings.from_env())
            self.assertEqual(observed, [])

    def test_bound_stops_unexpected_attempt_and_budget(self):
        with self.session() as (observed, _, _):
            bound = integration.Bound(reg.ROOT, [('A','generation')], 32000)
            ids = bound.reserve(1,32000,{'mode':'A'})
            with self.assertRaises(live.LiveBlocked):
                bound.reserve(1,32000,{'mode':'B'})
            with self.assertRaises(live.LiveBlocked):
                bound.call([], {}, 'screening', ids[0])
            self.assertEqual(observed, [])

    def test_results_list_excludes_diagnostic_only_folders_without_deleting_them(self):
        from app.api.runtime import results
        with self.session():
            root = reg.ROOT/'experiments'
            for name in ('readable', 'historical-diagnostic-only'):
                (root/name).mkdir(parents=True)
            (root/'readable'/'experiment.json').write_text('{"specification":{}}')
            (root/'historical-diagnostic-only'/'integration-diagnostics.json').write_text('{"preserved":true}')
            self.assertEqual(results()['runs'], ['readable'])
            self.assertTrue((root/'historical-diagnostic-only'/'integration-diagnostics.json').is_file())

    def integration_fixture(self, a, path):
        draft = a.model_dump(mode='json')|{'activated_at':None, 'expires_at':'2000-01-01T00:00:00Z'}
        path.write_text(json.dumps(draft))
        dataset = reg.ROOT/'dataset'
        dataset.mkdir()
        data = {'cases': [{'case_id':'development-02', 'split':'development', 'fixtures':['fixture'],
                          'query':'When are mentor check-ins?', 'adversarial':False, 'channel':None}]}
        snapshot = {'dataset_hash':exp.digest(data), 'configuration':{'synthetic':True},
                    'parser_version':exp.PARSER_VERSION, 'chunk_size':exp.settings.chunk_size,
                    'chunk_overlap':exp.settings.chunk_overlap,
                    'items':{'fixture':{'id':'v1','document_id':'d1'}}}
        (dataset/'snapshot.json').write_text(json.dumps(snapshot))
        (dataset/'annotations.json').write_text('{"synthetic":true}')
        return data, dataset

    def test_bounded_baseline_then_paired_exact_five_calls_and_zero_capacity(self):
        with self.session() as (observed, a, path):
            data, dataset = self.integration_fixture(a, path)
            clock = [0.0]
            waits = []
            def sleep(seconds):
                self.assertLessEqual(seconds,60)
                waits.append(seconds)
                clock[0] += seconds
            original = integration.Bound
            def bound(*args):
                return original(*args, clock=lambda:clock[0], sleep=sleep)
            with patch.dict(os.environ, {'LIVE_LLM_ENABLED':'false'}), \
                 patch.object(exp, 'DATASET', dataset), patch.object(exp, 'load', return_value=data), \
                 patch.object(exp.indexer, 'index_configuration', return_value={'synthetic':True}), \
                 patch.object(exp, 'search', return_value=INITIAL), \
                 patch.object(exp, 'report'), patch.object(exp, 'git_state', return_value={'synthetic':True}), \
                 patch.object(integration, 'identity', return_value={'synthetic':True}), \
                 patch.object(integration, 'Bound', side_effect=bound):
                result = integration.execute()
                self.assertEqual(result['outcome'],'answered')
                with self.assertRaises(live.LiveBlocked):
                    integration.execute(paired=True)
                self.assertEqual(len(observed),1)
                result = integration.execute(paired=True, source_review_note='Synthetic source-supported fixture review only')
                self.assertEqual(result['outcome'],'completed_review_pending')
                self.assertEqual(result['capacity']['remaining_calls'],0)
                self.assertEqual(result['capacity']['remaining_reserved_tokens'],0)
                self.assertEqual(len(observed),5)
                self.assertEqual(sum(waits),260)
                self.assertFalse(LiveSettings.from_env().enabled)
                for mode in 'ABC':
                    row = json.loads((reg.ROOT/'experiments'/integration.PAIRED/f'case-development-02-{mode}-0.json').read_text())
                    self.assertEqual(row['response']['candidate_evidence'], INITIAL['hits'])
                with self.assertRaises(live.LiveBlocked):
                    integration.execute()

    def test_failed_baseline_prevents_pair_and_preserves_partial(self):
        with self.session(status=500) as (observed, a, path):
            data, dataset = self.integration_fixture(a, path)
            with patch.dict(os.environ, {'LIVE_LLM_ENABLED':'false'}), \
                 patch.object(exp, 'DATASET', dataset), patch.object(exp, 'load', return_value=data), \
                 patch.object(exp.indexer, 'index_configuration', return_value={'synthetic':True}), \
                 patch.object(exp, 'search', return_value=INITIAL), \
                 patch.object(integration, 'identity', return_value={'synthetic':True}):
                with self.assertRaises(live.LiveBlocked):
                    integration.execute()
                diagnostic = json.loads((reg.ROOT/'experiments'/integration.BASELINE/'integration-diagnostics.json').read_text())
                self.assertEqual(diagnostic['outcome'],'stopped_no_retry')
                self.assertEqual(len(diagnostic['attempts']),1)
                self.assertEqual(diagnostic['accounting_after']['reserved_tokens_used'],32000)
                with self.assertRaises(live.LiveBlocked):
                    integration.execute(paired=True,source_review_note='Cannot authorize a failed baseline')
                self.assertEqual(len(observed),1)
                self.assertFalse((reg.ROOT/'experiments'/integration.PAIRED).exists())


if __name__ == '__main__':
    unittest.main()
