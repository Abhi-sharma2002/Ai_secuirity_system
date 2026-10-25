"""Human form mechanics with explicit synthetic labels in temporary directories."""
import csv
from copy import deepcopy
from unittest.mock import patch

import pytest

from app.evaluation import simple_reporting as report, simple_review as review
from app.evaluation.simple_config import EvaluationError
from scripts.run_eval import COLUMNS
from backend.tests.evaluation.test_simple_reporting import DATA, row


def records(tmp_path):
    path = tmp_path / 'records.csv'
    rows = [row(case, mode) for case in DATA['cases'] for mode in 'ABC']
    report.write_csv(path, COLUMNS, rows)
    return path, rows


def read_csv(path):
    with path.open(newline='') as handle:
        return list(csv.DictReader(handle))


def test_empty_preparation_never_fabricates_human_rows(tmp_path):
    status = review.prepare(tmp_path / 'records.csv', tmp_path)
    assert status['status'] == 'no_records'
    assert status['n_sample_rows'] == 0
    assert status['agreement'] is None
    assert read_csv(tmp_path / 'spot_check.csv') == []
    assert not (tmp_path / 'records.csv').exists()


def test_seeded_sample_is_stable_has_ten_per_mode_and_no_labels(tmp_path):
    path, rows = records(tmp_path)
    with patch('socket.socket.connect', side_effect=AssertionError('Network forbidden')):
        status = review.prepare(path, tmp_path)
    sample = read_csv(tmp_path / 'spot_check.csv')
    assert status['status'] == 'sample_ready'
    assert len(sample) == 30
    assert all(sum(r['mode'] == m for r in sample) == 10 for m in 'ABC')
    assert sample == read_csv(tmp_path / 'spot_check.csv')
    reversed_sample = report.sample_rows(list(reversed(rows)))
    assert [(r['case_id'], r['mode']) for r in sample] == [(r['case_id'], r['mode']) for r in reversed_sample]
    assert all(not r[k] for r in sample for k in ('attack_correct', 'task_correct', 'quality_0_4', 'reviewer'))
    review.prepare(path, tmp_path)
    assert sample == read_csv(tmp_path / 'spot_check.csv')


def test_review_requires_explicit_labels_and_preserves_old_records(tmp_path):
    path, rows = records(tmp_path)
    pending = next(r for r in rows if r['case_id'] == 'final-23' and r['mode'] == 'A')
    pending.update(needs_review='true', attack_succeeded='', task_passed='')
    report.write_csv(path, COLUMNS, rows)
    before = path.read_bytes()
    status = review.prepare(path, tmp_path)
    assert status['n_pending_review'] == 1
    assert status['n_sample_rows'] == 0
    forms = read_csv(tmp_path / 'review_decisions.csv')
    with patch.object(review, 'ROOT', tmp_path), pytest.raises(EvaluationError):
        review.apply_decisions(path, tmp_path / 'review_decisions.csv')
    assert path.read_bytes() == before
    forms[0].update(attack_succeeded='false', task_passed='true', reviewer='SYNTHETIC TEST LABEL', rationale='Synthetic mechanics only')
    report.write_csv(tmp_path / 'review_decisions.csv', review.REVIEW_COLUMNS, forms)
    with patch.object(review, 'ROOT', tmp_path):
        result = review.apply_decisions(path, tmp_path / 'review_decisions.csv')
    assert result['n_applied'] == 1
    assert next((tmp_path / 'archive/evaluation_reviews').glob('*/records.before.csv')).read_bytes() == before
    updated = next(r for r in report.read_records(path) if (r['case_id'], r['mode']) == ('final-23', 'A'))
    assert updated['needs_review'] == 'false' and updated['task_passed'] == 'true'
    assert review.prepare(path, tmp_path)['n_sample_rows'] == 30


def test_semantic_evidence_removal_requires_human_choice(tmp_path):
    path, rows = records(tmp_path)
    pending = next(r for r in rows if r['case_id'] == 'final-03' and r['mode'] == 'C')
    pending.update(needs_review='true', task_passed='', answer_chunk_removed='')
    report.write_csv(path, COLUMNS, rows)
    review.prepare(path, tmp_path)
    forms = read_csv(tmp_path / 'review_decisions.csv')
    forms[0].update(task_passed='true', reviewer='SYNTHETIC TEST LABEL', rationale='Synthetic mechanics only')
    report.write_csv(tmp_path / 'review_decisions.csv', review.REVIEW_COLUMNS, forms)
    with pytest.raises(EvaluationError, match='removal requires'):
        review.apply_decisions(path, tmp_path / 'review_decisions.csv')
    forms[0]['answer_chunk_removed'] = 'true'
    report.write_csv(tmp_path / 'review_decisions.csv', review.REVIEW_COLUMNS, forms)
    with patch.object(review, 'ROOT', tmp_path):
        review.apply_decisions(path, tmp_path / 'review_decisions.csv')
    changed = next(r for r in report.read_records(path) if (r['case_id'], r['mode']) == ('final-03', 'C'))
    assert changed['answer_chunk_removed'] == 'true'


def test_quality_and_agreement_require_explicit_complete_human_fields(tmp_path):
    path, rows = records(tmp_path)
    review.prepare(path, tmp_path)
    checks = read_csv(tmp_path / 'spot_check.csv')
    selected = checks[0]
    selected.update(task_correct='true', quality_0_4='3', reviewer='SYNTHETIC TEST LABEL')
    if selected['automated_attack_succeeded']:
        selected['attack_correct'] = 'false'
    report.write_csv(tmp_path / 'spot_check.csv', review.SPOT_COLUMNS, checks)
    reviewed = report.read_spot_checks(tmp_path / 'spot_check.csv', rows)
    assert len(reviewed) == 1 and reviewed[0]['quality'] == 3
    summary = report.summarize(rows, DATA, reviewed)
    assert summary[0]['n_quality'] == 1
    assert summary[0]['mean_quality'] == 3
    checks[0]['quality_0_4'] = ''
    report.write_csv(tmp_path / 'spot_check.csv', review.SPOT_COLUMNS, checks)
    with pytest.raises(EvaluationError):
        report.read_spot_checks(tmp_path / 'spot_check.csv', rows)


def test_partial_run_cannot_claim_complete_spot_check(tmp_path):
    path, rows = records(tmp_path)
    report.write_csv(path, COLUMNS, rows[:9])
    status = review.prepare(path, tmp_path)
    assert status['status'] == 'waiting_for_complete_comparison'
    assert status['n_sample_rows'] == 0


def test_changed_record_cannot_accept_stale_review(tmp_path):
    path, rows = records(tmp_path)
    rows[0].update(needs_review='true', task_passed='')
    report.write_csv(path, COLUMNS, rows)
    review.prepare(path, tmp_path)
    forms = read_csv(tmp_path / 'review_decisions.csv')
    forms[0].update(task_passed='true', reviewer='SYNTHETIC TEST LABEL', rationale='Test')
    report.write_csv(tmp_path / 'review_decisions.csv', review.REVIEW_COLUMNS, forms)
    rows[0]['answer'] = 'Changed answer'
    report.write_csv(path, COLUMNS, rows)
    with pytest.raises(EvaluationError, match='changed record'):
        review.apply_decisions(path, tmp_path / 'review_decisions.csv')
