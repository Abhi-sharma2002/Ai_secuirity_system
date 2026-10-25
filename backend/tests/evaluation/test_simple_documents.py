"""Written report checks use temporary synthetic fixtures, never production results."""
import csv
from unittest.mock import patch

import pytest

from app.evaluation import simple_documents as docs, simple_reporting as report
from app.evaluation.simple_config import EvaluationError
from backend.tests.evaluation.test_simple_reporting import DATA, ATTACKS, row
from scripts.run_eval import COLUMNS


def source(tmp_path, rows=()):
    results = tmp_path / 'results'
    results.mkdir()
    if rows:
        report.write_csv(results / 'records.csv', COLUMNS, rows)
    report.write_csv(results / 'summary.csv', report.SUMMARY_COLUMNS, report.summarize(rows, DATA))
    return results


def test_empty_report_is_honest_and_has_required_heading_order(tmp_path):
    results = source(tmp_path)
    output = tmp_path / 'docs'
    with patch('socket.socket.connect', side_effect=AssertionError('Network forbidden')):
        status = docs.write_documents(results, output)
    text = (output / 'REPORT.md').read_text()
    assert 'No measured security/usability winner' in text
    assert [line[3:] for line in text.splitlines() if line.startswith('## ')] == docs.HEADINGS
    assert 'No eligible successful-attack rows' in text
    assert 'Worked example pending' in (output / 'METRICS_EXPLAINED.md').read_text()
    assert status['comparison_and_human_sample_complete'] is False
    assert docs.write_documents(results, output, check=True)['status'] == 'verified'


def test_changed_summary_cannot_generate_a_report(tmp_path):
    results = source(tmp_path)
    text = (results / 'summary.csv').read_text().replace('A,', 'Z,', 1)
    (results / 'summary.csv').write_text(text)
    with pytest.raises(EvaluationError, match='does not match'):
        docs.write_documents(results, tmp_path / 'docs')


def test_check_detects_manually_invented_written_numbers(tmp_path):
    results = source(tmp_path)
    output = tmp_path / 'docs'
    docs.write_documents(results, output)
    path = output / 'REPORT.md'
    path.write_text(path.read_text().replace('0 recorded', '999 recorded', 1))
    with pytest.raises(EvaluationError, match='differs'):
        docs.write_documents(results, output, check=True)


def test_only_eligible_attack_successes_are_quoted_and_examples_use_relevant_rows(tmp_path):
    rows = [row(ATTACKS[0], answer='SYNTHETIC TEST SUCCESS', attack_succeeded='true'),
            row(ATTACKS[1], answer='SYNTHETIC ERROR ANSWER', error='Provider error', attack_succeeded='true'),
            row(ATTACKS[2], answer='SYNTHETIC UNREVIEWED ANSWER', needs_review='true', attack_succeeded='true')]
    results = source(tmp_path, rows)
    documents, _ = docs.render(results)
    assert '> SYNTHETIC TEST SUCCESS' in documents['REPORT.md']
    assert '> SYNTHETIC ERROR ANSWER' not in documents['REPORT.md']
    assert '> SYNTHETIC UNREVIEWED ANSWER' not in documents['REPORT.md']
    assert ATTACKS[0]['case_id'] + '=true' in documents['METRICS_EXPLAINED.md']


def test_all_rates_have_formulas_meanings_and_examples(tmp_path):
    documents, _ = docs.render(source(tmp_path))
    for metric in report.RATES:
        assert '## ' + metric in documents['METRICS_EXPLAINED.md']
        assert docs.RATE_FORMULAS[metric] in documents['METRICS_EXPLAINED.md']
        assert docs.MEANINGS[metric] in documents['METRICS_EXPLAINED.md']


def test_actual_row_rates_are_checked_before_writing(tmp_path):
    rows = [row(), row(ATTACKS[0], attack_succeeded='true')]
    results = source(tmp_path, rows)
    with (results / 'summary.csv').open() as handle:
        summary = list(csv.DictReader(handle))
    summary[0]['asr_all'] = '.25'
    report.write_csv(results / 'summary.csv', report.SUMMARY_COLUMNS, summary)
    with pytest.raises(EvaluationError):
        docs.render(results)
