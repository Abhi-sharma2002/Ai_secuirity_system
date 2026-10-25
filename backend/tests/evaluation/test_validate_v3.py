"""Local dataset integrity checks; no retrieval, model calls or response grading."""
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

from scripts import validate_v3 as validator
from scripts.validate_v3 import DATASET, validate


class V3ValidationTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name) / 'benchmark_v3'
        shutil.copytree(DATASET, self.root)
        self.data = json.loads((self.root / 'manifest.json').read_text())

    def save(self):
        raw = (json.dumps(self.data, indent=2) + '\n').encode()
        (self.root / 'manifest.json').write_bytes(raw)
        (self.root / 'manifest.sha256').write_text(hashlib.sha256(raw).hexdigest() + '\n')

    def case(self, case_id):
        return next(c for c in self.data['cases'] if c['case_id'] == case_id)

    def test_valid_dataset_preserves_contextual_false_value_exception(self):
        report = validate(self.root)
        self.assertEqual(report['n_cases'], len(self.data['cases']))
        self.assertEqual(report['channels']['direct'], 5)
        self.assertEqual(report['subtypes']['misinformation'], 4)
        self.assertTrue(report['original_benchmark_unchanged'])

    def original_without_runtime_snapshot(self):
        source = self.root.parent / 'original'
        shutil.copytree(validator.SOURCE, source)
        snapshot = source / 'snapshot.json'
        if snapshot.exists():
            snapshot.rename(self.root.parent / 'preserved-original-snapshot.json')
        return source

    def test_fresh_checkout_uses_identical_preserved_snapshot_only_when_missing(self):
        source = self.original_without_runtime_snapshot()
        with patch.object(validator, 'SOURCE', source):
            self.assertTrue(validate(self.root)['original_benchmark_unchanged'])
        self.assertFalse((source / 'snapshot.json').exists())

    def test_preserved_snapshot_cannot_hide_changed_original_snapshot(self):
        source = self.original_without_runtime_snapshot()
        (source / 'snapshot.json').write_text('Synthetic changed original')
        with patch.object(validator, 'SOURCE', source), self.assertRaisesRegex(ValueError, 'Original benchmark changed'):
            validate(self.root)

    def test_fresh_checkout_rejects_changed_preserved_snapshot(self):
        source = self.original_without_runtime_snapshot()
        (self.root / 'snapshot.json').write_text('Synthetic changed preserved copy')
        with patch.object(validator, 'SOURCE', source), self.assertRaisesRegex(ValueError, 'Original benchmark changed'):
            validate(self.root)

    def test_missing_keywords_rejected(self):
        self.case('development-01')['expected_keywords'] = []
        self.save()
        with self.assertRaisesRegex(ValueError, 'missing expected keywords'):
            validate(self.root)

    def test_missing_canary_rejected(self):
        del self.case('final-16')['canary']
        self.save()
        with self.assertRaisesRegex(ValueError, 'missing canary'):
            validate(self.root)

    def test_duplicate_canary_rejected(self):
        self.case('final-17')['canary'] = self.case('final-16')['canary']
        self.save()
        with self.assertRaisesRegex(ValueError, 'duplicate canary'):
            validate(self.root)

    def test_direct_canary_cannot_leak_into_any_document(self):
        fixture = next(f for f in self.data['fixtures'] if f['fixture_id'] == 'v3-misinfo-01')
        path = self.root / fixture['path']
        path.write_text(path.read_text() + '\nBLUE FALCON\n')
        fixture['sha256'] = hashlib.sha256(path.read_bytes()).hexdigest()
        self.save()
        with self.assertRaisesRegex(ValueError, 'direct canary must occur only in query'):
            validate(self.root)

    def test_semantic_review_cannot_be_disabled(self):
        self.case('final-02')['human_review_required'] = False
        self.save()
        with self.assertRaisesRegex(ValueError, 'semantic case must retain its behavior and require human review'):
            validate(self.root)

    def test_false_fact_scope_cannot_silently_change(self):
        self.case('final-23')['planted_false_context'] = 'badge duration'
        self.save()
        with self.assertRaisesRegex(ValueError, 'invalid approved false-fact scope'):
            validate(self.root)

    def test_new_false_value_in_benign_document_rejected(self):
        fid = 'synthetic-benign'
        text = 'Fictional benign allowance is 5000 rupees.'
        path = self.root / 'documents/synthetic-benign.txt'
        path.write_text(text)
        self.data['fixtures'].append({'fixture_id': fid, 'path': 'documents/synthetic-benign.txt',
                                     'sha256': hashlib.sha256(path.read_bytes()).hexdigest()})
        self.data['cases'].append({'case_id': fid, 'fixtures': [fid], 'expected_evidence': [fid],
                                  'expected_task': '5000 rupees', 'expected_keywords': ['5000'],
                                  'expected_behavior': 'answer', 'human_review_required': False,
                                  'supporting_quotes': [text], 'adversarial': False})
        self.save()
        with self.assertRaisesRegex(ValueError, 'false fact in benign document'):
            validate(self.root)
