"""Bounded paid authorization; synthetic transport and temporary accounting only."""
import json
import os
from datetime import timedelta
import unittest
from unittest.mock import patch
from pydantic import ValidationError
from backend.tests.llm import test_azure_openai as fixtures
from app.llm import client as live
from app.rag import assistant
from scripts import azure_live_integration as integration


class PaidAzureTests(unittest.TestCase):
    def test_retired_paid_development_command_blocks_before_any_activation(self):
        from scripts import run_authorized_development
        with fixtures.AzureTests().session() as (requests, a, path):
            before = path.read_bytes()
            with self.assertRaisesRegex(live.LiveBlocked, 'trial-credit-only'):
                run_authorized_development.main()
            self.assertEqual(path.read_bytes(), before)
            self.assertEqual(requests, [])

    def paid(self, a):
        return a.model_dump() | {'confirmed_free_promotional': False,
            'eligibility_evidence': None, 'eligibility_checked_at': None,
            'entitlement_expiry': 'unknown', 'paid_azure_test_authorized': True,
            'paid_authorization_basis': 'User accepts Azure charges for five attempts and 160000 local units for one hour.'}

    def test_historical_paid_receipt_is_readable_but_cannot_authorize_calls(self):
        with fixtures.AzureTests().session() as (requests, a, path):
            historical = live.Approval(**self.paid(a))
            serialized = historical.model_dump_json()
            self.assertEqual(live.Approval.model_validate_json(serialized).model_dump_json(), serialized)
            path.write_text(serialized)
            for free_only in ('true', 'false'):
                with patch.dict(os.environ, {'FREE_ONLY': free_only}):
                    with self.assertRaisesRegex(live.LiveBlocked, 'trial-credit-only'):
                        live.approval()
                    self.assertEqual(assistant.respond('When?', 'A', initial=fixtures.INITIAL)['status'], 'live_blocked')
            self.assertEqual(requests, [])
            self.assertEqual(live.allowance_capacity(historical)['remaining_calls'], 5)

    def test_paid_limits_basis_and_window_enforced(self):
        with fixtures.AzureTests().session() as (_,a,_):
            values=self.paid(a)
            for edit in ({'max_calls':6},{'max_reserved_tokens':160001},
                         {'paid_authorization_basis':None},{'provider':'groq'},
                         {'expires_at':a.expires_at+timedelta(seconds=1)},
                         {'confirmed_free_promotional':True}):
                with self.subTest(edit=edit),self.assertRaises(ValidationError):
                    live.Approval(**(values|edit))

    def test_free_only_and_unapproved_paid_modes_block(self):
        with fixtures.AzureTests().session() as (requests,a,path):
            with patch.dict(os.environ,{'FREE_ONLY':'false'}),self.assertRaises(live.LiveBlocked):
                live.approval()
            path.write_text(live.Approval(**self.paid(a)).model_dump_json())
            with self.assertRaises(live.LiveBlocked):live.approval()
            self.assertEqual(requests,[])

    def test_paid_mode_blocks_before_transport_even_if_provider_would_return_quota_error(self):
        with fixtures.AzureTests().session(status=429) as (requests, a, path):
            path.write_text(live.Approval(**self.paid(a)).model_dump_json())
            with patch.dict(os.environ, {'FREE_ONLY': 'false'}):
                self.assertEqual(assistant.respond('When?', 'A', initial=fixtures.INITIAL)['status'], 'live_blocked')
                with self.assertRaises(live.LiveBlocked):
                    live.reserve(1, 32000)
            self.assertEqual(requests, [])

    def test_paid_activation_refused_without_rewriting_receipt(self):
        from app.core.config import LiveSettings
        with fixtures.AzureTests().session() as (_, a, path):
            self.assertNotIn('paid_azure_test_authorized', json.loads(a.model_dump_json()))
            values = self.paid(a) | {'activated_at': None, 'expires_at': '2000-01-01T00:00:00Z'}
            path.write_text(json.dumps(values, default=str))
            before = path.read_bytes()
            with self.assertRaisesRegex(live.LiveBlocked, 'trial-credit-only'):
                integration.activate(LiveSettings.from_env())
            self.assertEqual(path.read_bytes(), before)

    def test_historical_paid_receipt_never_reaches_answer_or_citation_validation(self):
        with fixtures.AzureTests().session(answer=fixtures.ANSWER | {'source_ids': ['unknown']}) as (requests, a, path):
            path.write_text(live.Approval(**self.paid(a)).model_dump_json())
            with patch.dict(os.environ, {'FREE_ONLY': 'false'}):
                self.assertEqual(assistant.respond('When?', 'A', initial=fixtures.INITIAL)['status'], 'live_blocked')
            self.assertEqual(requests, [])
