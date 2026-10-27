"""Case scoring must remain traceable to unchanged evidence and recorded outcomes."""
import json
from copy import deepcopy
import pytest
from app.evaluation.case_audit import audit_cases, write_case_audit
from app.evaluation.simple_config import EvaluationError
from app.evaluation.simple_index import digest
from backend.tests.evaluation.test_simple_reporting import DATA, BENIGN, row


def evidence(tmp_path, case):
    fixture = next(f for f in DATA['fixtures'] if f['fixture_id'] == case['expected_evidence'][0])
    hit = {'id': 'test-chunk', 'document_id': fixture['fixture_id'], 'sha256': fixture['sha256'],
           'text': case['supporting_quotes'][0]}
    content = {'hits': [hit], 'error': ''}
    trace = dict(case_id=case['case_id'], query=case['query'], doc_ids=case['fixtures'],
                 **content, content_sha256=digest(content))
    folder = tmp_path / 'retrieval'
    folder.mkdir()
    path = folder / (case['case_id'] + '.json')
    path.write_text(json.dumps(trace))
    return hit, path, trace


def test_recomputed_case_grade_has_support_and_preserves_historical_trace(tmp_path):
    case = BENIGN[0]
    hit, _, _ = evidence(tmp_path, case)
    saved = row(case, answer=case['expected_task'], retrieved_chunk_ids=json.dumps([hit['id']]),
                sources=json.dumps([hit]))
    before = deepcopy(saved)
    values = audit_cases([saved], DATA, tmp_path)
    observed = next(v for v in values if v['case_id'] == case['case_id'] and v['mode'] == 'A')
    assert observed['score_differences'] == {}
    assert observed['saved_grades']['task_passed'] is True
    assert all(observed['keyword_matches'].values())
    assert observed['quote_observations'][0]['in_single_retained_chunk'] is True
    assert observed['historical_retention_missing'] is True
    assert sum(v['state'] == 'not_run' for v in values) == 140
    assert saved == before


def test_wrong_saved_grade_is_reported_not_silently_rewritten(tmp_path):
    case = BENIGN[0]
    hit, _, _ = evidence(tmp_path, case)
    saved = row(case, answer='Wrong fact.', retrieved_chunk_ids=json.dumps([hit['id']]), sources=json.dumps([hit]))
    observed = audit_cases([saved], DATA, tmp_path)[0]
    assert observed['score_differences']['task_passed'] == {'saved': True, 'recomputed': False}
    assert saved['task_passed'] == 'true'


def test_evidence_tampering_or_missing_trace_prevents_audit(tmp_path):
    case = BENIGN[0]
    hit, path, trace = evidence(tmp_path, case)
    saved = row(case, retrieved_chunk_ids=json.dumps([hit['id']]))
    trace['hits'][0]['text'] = 'Changed evidence'
    path.write_text(json.dumps(trace))
    with pytest.raises(EvaluationError, match='integrity'):
        audit_cases([saved], DATA, tmp_path)
    path.unlink()
    with pytest.raises(EvaluationError, match='missing original'):
        audit_cases([saved], DATA, tmp_path)


def test_no_observations_export_only_plans_without_invented_grades(tmp_path):
    status = write_case_audit(tmp_path, tmp_path / 'records.csv', [], DATA)
    assert status['recorded_rows'] == 0
    assert status['missing_rows'] == 141
    assert status['score_difference_rows'] == 0
    assert status['provider_requests_made'] == 0
    values = json.loads((tmp_path / 'case_evaluation.json').read_text())['cases']
    assert all(v['saved_grades'] is None and v['answer'] is None for v in values)
