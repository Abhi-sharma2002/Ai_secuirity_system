"""Offline reservation-contract tests; dummy approvals, provider I/O forbidden."""
import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from app.storage import registry as reg
from app.llm import client as live


class ReservationContractTests(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        root = patch.object(reg, 'ROOT', Path(folder.name))
        root.start()
        self.addCleanup(root.stop)
        network = patch('socket.socket.connect', side_effect=AssertionError('Network forbidden'))
        network.start()
        self.addCleanup(network.stop)
        reg.initialize()
        self.approved = live.Approval(
            provider='groq', allowance_id='OFFLINE-CONTRACT', confirmed_free_promotional=True,
            approved_model='dummy-model', expires_at=datetime.now(timezone.utc)+timedelta(hours=1),
            max_calls=4, max_reserved_tokens=128000, chat_completions_supported=True,
            structured_outputs_supported=True, max_output_tokens_supported=True,
            confirmation_note='OFFLINE TEST ONLY; no provider calls')

    def test_changed_approval_cannot_consume_existing_reservation(self):
        with patch.object(live, 'approval', return_value=self.approved):
            reservation = live.reserve(1, 32000)[0]
        for changes in ({'approved_model': 'different-model'}, {'max_calls': 1},
                        {'expires_at': self.approved.expires_at + timedelta(hours=1)}):
            with self.subTest(changes=changes), patch.object(
                    live, 'approval', return_value=self.approved.model_copy(update=changes)):
                with self.assertRaisesRegex(live.LiveBlocked, 'approval changed'):
                    live.call([], {}, 'generation', reservation)
        with reg.connect() as db:
            row = db.execute('SELECT * FROM calls WHERE id=?', (reservation,)).fetchone()
            self.assertEqual(row['status'], 'reserved')
            self.assertNotIn('started_at', json.loads(row['data']))

    def test_invalid_reservations_leave_ledger_unchanged(self):
        for calls, tokens in ((0, 100), (-1, 100), (True, 100), (1.5, 100),
                              (1, 0), (1, -1), (1, True), (1, 1.5), (2, 1)):
            with self.subTest(calls=calls, tokens=tokens), patch.object(
                    live, 'approval', return_value=self.approved):
                with self.assertRaises(live.LiveBlocked):
                    live.reserve(calls, tokens)
            with reg.connect() as db:
                self.assertEqual(db.execute('SELECT COUNT(*) FROM calls').fetchone()[0], 0)
                self.assertEqual(db.execute('SELECT COUNT(*) FROM allowance').fetchone()[0], 0)

    def test_edit_does_not_reset_cumulative_budget(self):
        with patch.object(live, 'approval', return_value=self.approved):
            live.reserve(1, 32000)
        changed = self.approved.model_copy(update={'max_calls': 1})
        with patch.object(live, 'approval', return_value=changed):
            with self.assertRaisesRegex(live.LiveBlocked, 'exhausted'):
                live.reserve(1, 32000)
