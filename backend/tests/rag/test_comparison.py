import tempfile
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from app.rag import comparison
from app.storage import registry
from app.api.runtime import Query, compare_query
from fastapi import HTTPException

INITIAL = {'hits':[{'id':'synthetic-1','text':'Fictional leave is 25 days.'}], 'snapshot':[], 'omitted_ids':[]}
CAPACITY = {'stopped':False, 'remaining_calls':4, 'remaining_reserved_tokens':128000}


class ComparisonTests(unittest.TestCase):
    def setUp(self):
        guard=patch('app.evaluation.comparison_provenance.capture', return_value={'synthetic': True})
        guard.start();self.addCleanup(guard.stop)

    def test_same_initial_evidence_and_no_grades(self):
        inputs=[]
        def respond(question, mode, **kwargs):
            inputs.append((mode, kwargs['initial']['hits'][0]['text']))
            kwargs['initial']['hits'][0]['text']='mutation inside synthetic response'
            return {'status':'answered', 'answer':'synthetic', 'mode':mode}
        with patch.object(comparison.live,'approval',return_value=SimpleNamespace()), patch.object(comparison.live,'allowance_capacity',return_value=CAPACITY), patch.object(comparison,'search',return_value=INITIAL), patch.object(comparison.live,'validate_interactive_input'), patch.object(comparison,'respond',side_effect=respond), patch('socket.socket.connect',side_effect=AssertionError('Network forbidden')):
            result=comparison.compare('Fictional query', 'synthetic-request')
        self.assertEqual([m for m,_ in inputs],list('ABC'))
        self.assertEqual({text for _,text in inputs},{INITIAL['hits'][0]['text']})
        self.assertEqual(result['review_status'],'unreviewed')
        self.assertEqual(result['not_executed_modes'],[])
        self.assertNotIn('attack_success', result)

    def test_capacity_gate_before_retrieval(self):
        for edit in ({'remaining_calls':3}, {'remaining_reserved_tokens':127999}, {'stopped':True}):
            with patch.object(comparison.live,'approval',return_value=SimpleNamespace()), patch.object(comparison.live,'allowance_capacity',return_value=CAPACITY|edit), patch.object(comparison,'search',side_effect=AssertionError('No retrieval')):
                self.assertEqual(comparison.compare('Fictional', 'id')['status'],'live_blocked')

    def test_error_stops_later_modes(self):
        with patch.object(comparison.live,'approval',return_value=SimpleNamespace()), patch.object(comparison.live,'allowance_capacity',return_value=CAPACITY), patch.object(comparison,'search',return_value=INITIAL), patch.object(comparison.live,'validate_interactive_input'), patch.object(comparison,'respond',return_value={'status':'llm_error'}) as answer:
            result=comparison.compare('Fictional', 'id')
        self.assertEqual(answer.call_count,1)
        self.assertEqual(result['not_executed_modes'],['B','C'])
        self.assertEqual(result['status'],'partial')

    def test_api_idempotency_without_provider(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(registry,'ROOT',Path(folder)), patch.object(comparison,'compare',return_value={'status':'completed','results':{}}) as execute:
            registry.initialize()
            query=Query(question='Fictional',request_id='synthetic-idempotent')
            self.assertEqual(compare_query(query),compare_query(query))
            self.assertEqual(execute.call_count,1)
            with self.assertRaises(HTTPException):
                compare_query(query.model_copy(update={'question':'Changed question'}))
