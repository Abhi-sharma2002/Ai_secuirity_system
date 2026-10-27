"""Synthetic arithmetic and chart checks in temporary directories only."""
import csv
import json
from pathlib import Path
import tempfile
from unittest.mock import patch

import pytest

from app.evaluation import simple_reporting as report
from app.evaluation.simple_config import EvaluationError, load_config
from scripts.run_eval import COLUMNS

DATA = report.manifest()
BENIGN = [c for c in DATA['cases'] if not c['adversarial']]
ATTACKS = [c for c in DATA['cases'] if c['adversarial']]


def row(case=None, mode='A', **changes):
    case = BENIGN[0] if case is None else case
    result = {k: '' for k in COLUMNS}
    result.update(case_id=case['case_id'], mode=mode, query=case['query'], model=load_config()['model'],
                  category=case.get('subtype') or 'benign', answer='Synthetic test answer.',
                  needs_review='false', attack_retrieved='true' if case['adversarial'] else 'false',
                  attack_succeeded='false' if case['adversarial'] else '', task_passed='true',
                  citation_correct='true', blocked='false', question_flagged='false', latency_s='2',
                  false_positive='false' if mode == 'C' and not case['adversarial'] else '',
                  answer_chunk_removed='false' if mode == 'C' and not case['adversarial'] else '')
    return {**result, **changes}


def test_missing_observations_are_unavailable():
    summary = report.summarize([], DATA)
    for mode in summary:
        assert mode['n_recorded'] == 0
        assert mode['n_missing'] == len(DATA['cases'])
        assert all(mode[key] is None for key in report.RATES)
        assert mode['mean_latency_s'] is None
        assert mode['mean_quality'] is None


def test_error_review_and_retrieval_denominators():
    rows = [row(ATTACKS[0], attack_succeeded='true'),
            row(ATTACKS[1], attack_retrieved='false'),
            row(ATTACKS[2], error='Provider filter', blocked='true', attack_succeeded='false'),
            row(ATTACKS[3], needs_review='true', attack_succeeded='')]
    mode = report.summarize(rows, DATA)[0]
    assert mode['asr_all'] == .5
    assert mode['asr_all_denominator'] == 2
    assert mode['asr_retrieved_only'] == 1
    assert mode['asr_retrieved_only_denominator'] == 1
    assert mode['n_errors'] == 1
    assert mode['n_needs_review'] == 1
    assert mode['n_latency'] == 4
    assert mode['mean_latency_s'] == 2


def test_false_positive_union_does_not_double_count():
    rows = [row(BENIGN[0], 'C', false_positive='true', answer_chunk_removed='true'),
            row(BENIGN[1], 'C', answer_chunk_removed='true'), row(BENIGN[2], 'C'),
            row(BENIGN[3], 'C', needs_review='true', answer_chunk_removed='')]
    mode = report.summarize(rows, DATA)[2]
    assert mode['false_positive_rate'] == 1 / 3
    assert mode['answer_chunk_removed_rate'] == 2 / 3
    assert mode['false_positive_total'] == 2 / 3
    assert mode['false_positive_total_denominator'] == 3
    assert report.summarize([row()], DATA)[0]['false_positive_rate'] is None


def test_citation_and_quality_denominators_and_nearest_rank_p95():
    rows = [row(c, latency_s=str(i + 1), citation_correct='true' if i == 0 else 'false')
            for i, c in enumerate(BENIGN[:4])]
    checks = [{'mode': 'A', 'quality': 4, 'agreed': True}, {'mode': 'A', 'quality': 2, 'agreed': False}]
    mode = report.summarize(rows, DATA, checks)[0]
    assert mode['citation_accuracy'] == .25
    assert mode['mean_latency_s'] == 2.5
    assert mode['p95_latency_s'] == 4
    assert mode['mean_quality'] == 3
    assert mode['n_quality'] == 2
    assert mode['agreement'] == .5


def test_record_reader_rejects_duplicates_nonfinite_and_mixed_model(tmp_path):
    path = tmp_path / 'records.csv'
    for rows in ([row(), row()], [row(latency_s='nan')], [row(model='different')]):
        report.write_csv(path, COLUMNS, rows)
        with pytest.raises(EvaluationError):
            report.read_records(path, DATA)


def test_spot_quality_requires_human_labels_bound_to_record(tmp_path):
    rows = [row()]
    sample = {'case_id': rows[0]['case_id'], 'mode': 'A', 'record_sha256': report.row_digest(rows[0]),
              'attack_correct': '', 'task_correct': '', 'quality_0_4': '', 'reviewer': ''}
    path = tmp_path / 'spot_check.csv'
    report.write_csv(path, list(sample), [sample])
    assert report.read_spot_checks(path, rows) == []
    reviewed = {**sample, 'task_correct': 'true', 'quality_0_4': '4', 'reviewer': 'SYNTHETIC TEST LABEL'}
    report.write_csv(path, list(sample), [reviewed])
    assert report.read_spot_checks(path, rows)[0]['quality'] == 4
    report.write_csv(path, list(sample), [{**reviewed, 'quality_0_4': '5'}])
    with pytest.raises(EvaluationError):
        report.read_spot_checks(path, rows)
    report.write_csv(path, list(sample), [{**reviewed, 'record_sha256': 'stale'}])
    with pytest.raises(EvaluationError):
        report.read_spot_checks(path, rows)


def test_no_records_report_produces_explicit_na_charts(tmp_path):
    from PIL import Image
    with patch('socket.socket.connect', side_effect=AssertionError('Network forbidden')):
        status = report.make_report(tmp_path / 'records.csv', tmp_path / 'out', data=DATA)
    assert status['status'] == 'no_records'
    assert status['n_records'] == 0
    assert status['provider_requests_made'] == 0
    assert not (tmp_path / 'records.csv').exists()
    with (tmp_path / 'out/summary.csv').open() as handle:
        summary = list(csv.DictReader(handle))
    assert [s['mode'] for s in summary] == list('ABC')
    assert all(s['asr_all'] == '' for s in summary)
    charts = list((tmp_path / 'out').glob('*.png'))
    assert len(charts) == 7
    for chart in charts:
        with Image.open(chart) as image:
            assert image.width > 500 and image.height > 300


def test_synthetic_metadata_cannot_write_production_results(tmp_path):
    (tmp_path / 'run_metadata.json').write_text(json.dumps({'origin': 'synthetic_test'}))
    with patch.object(report, 'ROOT', tmp_path), pytest.raises(EvaluationError):
        report.make_report(tmp_path / 'records.csv', tmp_path / 'results', data=DATA)
    assert not (tmp_path / 'results').exists()


def test_pdf_false_positive_includes_benign_source_flag_without_answer_loss():
    rows = [row(BENIGN[0], 'C', removed_chunk_ids='["unneeded-benign-chunk"]'),
            row(BENIGN[1], 'C'), row(BENIGN[2], 'C', blocked='true', question_flagged='true'),
            row(BENIGN[3], 'C', error='Synthetic operational error', blocked='true')]
    summary = report.summarize(rows, DATA)[2]
    assert summary['pdf_false_positive_rate'] == 2 / 3
    assert summary['pdf_false_positive_rate_numerator'] == 2
    assert summary['pdf_false_positive_rate_denominator'] == 3
    assert summary['answer_chunk_removed_rate'] == 0
