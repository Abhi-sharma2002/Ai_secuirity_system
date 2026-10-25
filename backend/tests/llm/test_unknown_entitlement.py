"""Narrow unknown-expiry amendment, offline only; no provider access."""
from datetime import datetime,timedelta,timezone
import json
import unittest
from unittest.mock import patch
from app.llm.client import Approval


class UnknownExpiryTests(unittest.TestCase):
    def setUp(self):
        guard=patch('socket.socket.connect',side_effect=AssertionError('Network forbidden'))
        guard.start();self.addCleanup(guard.stop)
        now=datetime.now(timezone.utc)
        self.values=dict(provider='nvidia_nim',allowance_id='TEST-ONLY',confirmed_free_promotional=True,
            approved_model='test',expires_at=now+timedelta(hours=1),max_calls=1,max_reserved_tokens=32000,
            chat_completions_supported=True,structured_outputs_supported=True,max_output_tokens_supported=True,
            confirmation_note='Synthetic test only',entitlement_expiry='unknown',
            eligibility_evidence='Synthetic operator-confirmed current free eligibility, not key expiry',
            eligibility_checked_at=now,activated_at=now)

    def test_recorded_unknown_with_one_hour_local_window(self):
        approval=Approval(**self.values)
        self.assertEqual(approval.entitlement_expiry,'unknown')
        self.assertEqual(approval.expires_at-approval.activated_at,timedelta(hours=1))

    def test_unverified_or_missing_evidence_rejected(self):
        for changes in ({'confirmed_free_promotional':False},{'eligibility_evidence':None},
                        {'eligibility_evidence':'   '},{'eligibility_checked_at':None}):
            with self.subTest(fields=list(changes)),self.assertRaises(ValueError):
                Approval(**(self.values|changes))

    def test_future_naive_and_unbounded_windows_rejected(self):
        now=self.values['activated_at']
        for changes in ({'eligibility_checked_at':now+timedelta(minutes=1)},
                        {'activated_at':now.replace(tzinfo=None)},
                        {'expires_at':now+timedelta(hours=2)},
                        {'expires_at':now+timedelta(minutes=30)}):
            with self.subTest(fields=list(changes)),self.assertRaises(ValueError):
                Approval(**(self.values|changes))

    def test_legacy_serialization_and_fingerprint_input_unchanged(self):
        legacy={k:v for k,v in self.values.items() if k not in (
            'entitlement_expiry','eligibility_evidence','eligibility_checked_at','activated_at')}
        a=Approval(**legacy)
        old={**legacy,'expires_at':legacy['expires_at'].isoformat().replace('+00:00','Z')}
        self.assertEqual(a.model_dump_json(),json.dumps(old,separators=(',',':')))
