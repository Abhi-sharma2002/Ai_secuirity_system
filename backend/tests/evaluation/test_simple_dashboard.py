"""Temporary synthetic CSVs exercise the read-only dashboard, never live models."""
import hashlib
import json
from unittest.mock import patch

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
import pytest

from app.api import runtime
from app.evaluation import simple_dashboard as dashboard, simple_reporting as report
from app.evaluation.simple_config import EvaluationError
from scripts.run_eval import COLUMNS
from backend.tests.evaluation.test_simple_reporting import DATA, BENIGN, ATTACKS, row


@pytest.fixture
def store(tmp_path, monkeypatch):
    monkeypatch.setattr(dashboard, 'ROOT', tmp_path)
    (tmp_path / 'results').mkdir()
    monkeypatch.setattr('app.llm.client.call', lambda *a, **kw: pytest.fail('No provider calls permitted'))
    return tmp_path / 'results'


def test_empty_dashboard_has_all_metrics_and_na_without_writes(store):
    report.make_report(store / 'records.csv', store, data=DATA)
    before = {p.name: p.read_bytes() for p in store.iterdir()}
    with patch('socket.socket.connect', side_effect=AssertionError('Network forbidden')):
        value = dashboard.snapshot()
    assert value['status'] == 'no_records'
    assert value['counts']['recorded'] == 0
    assert value['counts']['expected'] == len(DATA['cases']) * 3
    assert {r['mode'] for r in value['summary']} == set('ABC')
    assert all(r['asr_all'] is None and r['mean_quality'] is None for r in value['summary'])
    assert set(report.RATES) <= {d['key'] for d in value['definitions']}
    assert value['charts_current'] and set(dashboard.CHARTS) <= set(value['artifacts'])
    assert {p.name: p.read_bytes() for p in store.iterdir()} == before
    assert not (store / 'records.csv').exists()


def test_dashboard_uses_actual_denominators_excludes_errors_and_review(store):
    rows = [row(ATTACKS[0], attack_succeeded='true'), row(ATTACKS[1], attack_retrieved='false'),
            row(ATTACKS[2], error='Synthetic provider filter', attack_succeeded='false'),
            row(ATTACKS[3], needs_review='true', attack_succeeded=''),
            row(BENIGN[0], 'C', false_positive='true', answer_chunk_removed='true'),
            row(BENIGN[1], 'C')]
    report.write_csv(store / 'records.csv', COLUMNS, rows)
    value = dashboard.snapshot()
    a, _, c = value['summary']
    assert a['asr_all'] == .5 and a['asr_all_denominator'] == 2
    assert a['asr_retrieved_only'] == 1 and a['asr_retrieved_only_denominator'] == 1
    assert c['false_positive_total'] == .5 and c['false_positive_total_numerator'] == 1
    assert value['counts']['errors'] == 1 and value['counts']['needs_review'] == 1
    assert value['status'] == 'partial' and not value['charts_current']


def test_stale_charts_and_summaries_are_not_served_as_current(store):
    report.make_report(store / 'records.csv', store, data=DATA)
    report.write_csv(store / 'records.csv', COLUMNS, [row()])
    assert not dashboard.snapshot()['charts_current']
    with pytest.raises(HTTPException) as error:
        runtime.evaluation_artifact('asr.png')
    assert error.value.status_code == 409
    # Current metric computation is independent of stale saved summary values.
    assert dashboard.snapshot()['summary'][0]['benign_task_success'] == 1


def test_artifact_allowlist_and_symlinks(store):
    (store / 'records.csv').write_text('synthetic')
    assert dashboard.artifact_path('records.csv') == store / 'records.csv'
    for name in ('../.env', '.env', 'missing.csv'):
        with pytest.raises(FileNotFoundError):
            dashboard.artifact_path(name)
    (store / 'summary.csv').symlink_to(store / 'records.csv')
    with pytest.raises(FileNotFoundError):
        dashboard.artifact_path('summary.csv')
    with pytest.raises(EvaluationError):
        dashboard.snapshot()


def test_evidence_integrity_and_unknown_case(store):
    cid = DATA['cases'][0]['case_id']
    (store / 'retrieval').mkdir()
    content = {'hits': [{'id': 'synthetic-source', 'text': 'Synthetic policy.'}], 'error': ''}
    saved = {**content, 'case_id': cid,
             'content_sha256': hashlib.sha256(json.dumps(content, sort_keys=True).encode()).hexdigest()}
    path = store / 'retrieval' / (cid + '.json')
    path.write_text(json.dumps(saved))
    assert dashboard.evidence(cid) == saved
    saved['hits'][0]['text'] = 'Changed synthetic source'
    path.write_text(json.dumps(saved))
    with pytest.raises(EvaluationError):
        dashboard.evidence(cid)
    with pytest.raises(FileNotFoundError):
        dashboard.evidence('../.env')


def test_invalid_or_synthetic_run_metadata_is_not_a_measured_run(store):
    for metadata in ({'origin': 'synthetic_test'}, {'origin': 'application_execution', 'config': {}}):
        (store / 'run_metadata.json').write_text(json.dumps(metadata))
        with pytest.raises(EvaluationError):
            dashboard.snapshot()


def test_http_routes_read_without_model_or_registry_writes(store):
    app = FastAPI()
    app.include_router(runtime.router)
    with TestClient(app) as client:
        response = client.get('/evaluation-v3')
        assert response.status_code == 200 and response.json()['status'] == 'no_records'
        assert client.get('/evaluation-v3/artifacts/not-allowed.json').status_code == 404
        assert client.get('/evaluation-v3/evidence/unknown').status_code == 404
    assert list(store.iterdir()) == []


def test_dashboard_quality_requires_record_bound_human_labels(store):
    record = row()
    report.write_csv(store / 'records.csv', COLUMNS, [record])
    check = {'case_id': record['case_id'], 'mode': 'A', 'record_sha256': report.row_digest(record),
             'attack_correct': '', 'task_correct': 'true', 'quality_0_4': '3',
             'reviewer': 'SYNTHETIC TEST LABEL'}
    report.write_csv(store / 'spot_check.csv', list(check), [check])
    value = dashboard.snapshot()
    assert value['counts']['quality_reviewed'] == 1
    assert value['summary'][0]['mean_quality'] == 3
    assert value['summary'][0]['agreement'] == 1
    record['answer'] = 'Changed synthetic response'
    report.write_csv(store / 'records.csv', COLUMNS, [record])
    with pytest.raises(EvaluationError, match='stale'):
        dashboard.snapshot()
