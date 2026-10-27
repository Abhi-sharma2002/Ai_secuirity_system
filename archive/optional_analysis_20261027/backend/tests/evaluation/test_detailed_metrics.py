"""Known statistical examples and missing/error/matched-case regression checks."""
import json
import pytest
from app.evaluation.detailed_metrics import analyze, wilson, write_analysis
from backend.tests.evaluation.test_simple_reporting import DATA, ATTACKS, BENIGN, row


def test_wilson_zero_is_uncertain_and_empty_is_unavailable():
    assert wilson(0, 0) == (None, None)
    low, high = wilson(0, 4)
    assert low == pytest.approx(0, abs=1e-12)
    assert high == pytest.approx(.48989083645)
    low, high = wilson(5, 10)
    assert low == pytest.approx(.2365930905)
    assert high == pytest.approx(.7634069095)


def test_errors_pending_and_missing_expand_sensitivity_without_becoming_grades():
    rows = [row(ATTACKS[0], attack_succeeded='true'),
            row(ATTACKS[1], error='provider_content_filter', attack_succeeded='false'),
            row(ATTACKS[2], needs_review='true', attack_succeeded='')]
    result = analyze(rows, DATA)
    a = result['coverage'][0]
    assert a['adjudicated_attack_count'] == 1
    assert a['operational_errors'] == 1 and a['unresolved_review'] == 1
    assert a['unknown_attack_count'] == 25
    assert a['planned_asr_best_case'] == pytest.approx(1 / 26)
    assert a['planned_asr_worst_case'] == 1
    assert a['successful_route_timing_count'] == 2
    assert result['coverage'][1]['planned_asr_worst_case'] == 1
    assert result['intervals'][0]['denominator'] == 1


def test_matched_comparison_uses_common_eligible_case_ids_only():
    rows = [row(c, 'A', attack_succeeded='true') for c in ATTACKS[:6]]
    rows += [row(c, 'B', attack_succeeded='false') for c in ATTACKS[:6]]
    rows += [row(ATTACKS[6], 'A', attack_succeeded='true'),
             row(ATTACKS[6], 'B', error='error', attack_succeeded='false'),
             row(BENIGN[0], 'A'), row(BENIGN[0], 'B', task_passed='false')]
    result = analyze(rows, DATA)
    comparison = result['paired_comparisons'][0]
    assert comparison['matched_cases'] == 6
    assert comparison['left_only_true'] == 6
    assert comparison['right_minus_left'] == -1
    assert comparison['mcnemar_exact_p_unadjusted'] == .03125
    assert result['paired_comparisons'][1]['right_minus_left'] == -1
    assert result['paired_comparisons'][2]['matched_cases'] == 0
    assert result['paired_comparisons'][2]['mcnemar_exact_p_unadjusted'] is None


def test_exports_are_valid_without_observations_or_provider_calls(tmp_path, monkeypatch):
    monkeypatch.setattr('socket.socket.connect', lambda *a, **k: pytest.fail('Network forbidden'))
    result = write_analysis(tmp_path, [], DATA)
    assert result['provider_requests_made'] == 0
    assert result['human_quality_count'] == 0
    assert result['records_sha256'] is None
    assert json.loads((tmp_path / 'detailed_metrics.json').read_text()) == result
    assert 'N/A' in (tmp_path / 'DETAILED_EVALUATION.md').read_text()
    assert len(list(tmp_path.glob('detailed_*.csv'))) == 5


def test_saved_retrieval_quality_is_case_level_and_integrity_checked(tmp_path):
    from app.evaluation.detailed_metrics import retrieval_quality
    from app.evaluation.simple_index import digest
    from app.evaluation.simple_config import EvaluationError
    case = BENIGN[0]
    folder = tmp_path / 'retrieval'
    folder.mkdir()
    content = {'hits': [{'document_id': 'irrelevant'}, {'document_id': case['expected_evidence'][0]}], 'error': ''}
    trace = dict(case_id=case['case_id'], query=case['query'], doc_ids=case['fixtures'],
                 **content, content_sha256=digest(content))
    path = folder / (case['case_id'] + '.json')
    path.write_text(json.dumps(trace))
    result = retrieval_quality(tmp_path, DATA)
    assert len(result) == 1
    assert result[0]['expected_document_recall'] == 1
    assert result[0]['candidate_document_precision'] == .5
    assert result[0]['reciprocal_first_relevant_chunk_rank'] == .5
    trace['hits'].clear()
    path.write_text(json.dumps(trace))
    with pytest.raises(EvaluationError, match='integrity'):
        retrieval_quality(tmp_path, DATA)
