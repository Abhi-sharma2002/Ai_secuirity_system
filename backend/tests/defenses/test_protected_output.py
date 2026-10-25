"""Synthetic local checks, not evidence of model resistance."""
import json
import unittest
from unittest.mock import patch
from app.defenses import output_screening, baseline, instruction_separation
from app.rag import assistant
from frontend.presentation import metric_rows, page_label


class ProtectedOutputTests(unittest.TestCase):
    def test_candidate_limits(self):
        self.assertTrue(output_screening.contains_payment_card('Synthetic test: 4111 1111 1111 1111'))
        self.assertTrue(output_screening.contains_payment_card('Synthetic test: 4111-1111-1111-1111'))
        self.assertFalse(output_screening.contains_payment_card('Leave allowance is 25 days.'))
        self.assertFalse(output_screening.contains_payment_card('1111111111111111'))
        self.assertFalse(output_screening.contains_payment_card('4111111111111112'))

    def test_c_blocks_without_rewriting_evidence_or_a_b_outputs(self):
        initial = {'hits': [{'id':'s1','text':'Fictional evidence'}], 'snapshot':[], 'omitted_ids':[]}
        raw = json.dumps({'status':'answered','answer':'Synthetic number 4111111111111111','source_ids':['s1']})
        for mode in 'ABC':
            with patch.object(assistant.live, 'validate_interactive_input'), patch.object(assistant.live, 'reserve', return_value=['r1','r2']), patch.object(assistant.live, 'call', return_value=(raw, {})), patch.object(assistant.screening, 'apply', return_value=initial['hits']), patch('socket.socket.connect', side_effect=AssertionError('network forbidden')):
                result=assistant.respond('Synthetic question', mode, initial=initial)
            self.assertEqual(result['candidate_evidence'], initial['hits'])
            if mode == 'C':
                self.assertEqual(result['status'], 'policy_blocked')
                self.assertNotIn('4111111111111111', result['answer'])
                self.assertEqual(result['references'], [])
                self.assertEqual(result['output_screening']['candidate_answer_for_local_review']['answer'], json.loads(raw)['answer'])
            else:
                self.assertEqual(result['status'], 'answered')
                self.assertIn('4111111111111111', result['answer'])

    def test_trusted_rule_and_version(self):
        self.assertIn('payment-card', baseline.GROUND)
        self.assertIn('payment-card', instruction_separation.SEPARATION)
        self.assertNotEqual(baseline.PROMPT_VERSION, instruction_separation.PROMPT_VERSION)

    def test_missing_metrics_are_not_zero_and_page_zero_not_verified(self):
        row=metric_rows({'by_mode': {'A': {'attack_success': {'rate':None,'denominator':0}}}})[0]
        self.assertEqual(row['Attack success rate'], 'Not evaluable (n=0)')
        self.assertEqual(row['Quality / 4'], 'Unreviewed')
        self.assertEqual(page_label(0), 'Page not established')
