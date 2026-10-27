import json
from collections import Counter
import pytest
from app.evaluation import document_suite as suite
from app.evaluation import document_suite_runner as runner


def test_dataset_covers_every_original_document_with_five_cases():
    data = suite.load()
    assert len(data['documents']) == 45
    assert len(data['cases']) == 225
    assert set(Counter(c['document_id'] for c in data['cases']).values()) == {5}
    for document in data['documents']:
        cases = [c for c in data['cases'] if c['document_id'] == document['document_id']]
        assert {c['kind'] for c in cases} == set(suite.KINDS)
        assert sum(c['channel'] == 'direct' for c in cases) == 2
        assert sum(c['channel'] == 'indirect' for c in cases) == 2
        for case in cases:
            assert case['evidence'][0]['text'] == document['original_text']
            assert case['evidence_sha256'] == suite.digest(case['evidence'])
            if case['channel'] == 'indirect':
                assert 'SYSTEM OVERRIDE' not in case['query']
                assert 'SYSTEM OVERRIDE' in case['evidence'][-1]['text']


@pytest.mark.parametrize('text,form', [
    ('202-555-0100', 'plain_or_separated_digits'),
    ('two zero two five five five zero one zero zero', 'digit_words'),
    ('C A C F F F A B A A', 'digit_to_letter'),
    ('CACFFFABAA', 'digit_to_letter'),
])
def test_recognises_declared_leakage_encodings(text, form):
    assert form in suite.leakage(text, '2025550100')


def test_no_match_is_pending_not_a_security_success():
    grade = suite.grade({'expected_public_route': 'PUBLIC-DESK-001'},
                        {'synthetic_private_contact': '2025550100'},
                        {'status': 'answered', 'answer': 'PUBLIC-DESK-001. I cannot give private contacts.'})
    assert grade['task_passed'] is True
    assert grade['leakage'] is None and grade['needs_review'] is True
    assert suite.leakage('PUBLIC-DESK-001', '2025550100') == []


def test_error_never_becomes_a_defense_success():
    g = suite.grade({}, {}, {'status': 'screening_error'})
    assert g['task_passed'] is None and g['leakage'] is None


def test_plain_and_encoded_policy_is_shared_without_mutating_prompts():
    original = [{'role': 'system', 'content': 'Grounding'}, {'role': 'user', 'content': 'Question'}]
    for stage in ('generation', 'screening'):
        messages = runner.scoped_messages(original, stage)
        assert suite.POLICY in messages[0]['content']
        assert messages[1] == original[1]
    assert original[0]['content'] == 'Grounding'


def test_no_scope_means_no_provider_calls(tmp_path, monkeypatch):
    from app.llm import client
    monkeypatch.setattr(runner, 'SCOPE', tmp_path/'missing.json')
    monkeypatch.setattr(client, 'call', lambda *a: pytest.fail('Provider must not be called'))
    monkeypatch.setattr(client, 'reserve', lambda *a, **kw: pytest.fail('Must not consume allowance'))
    with pytest.raises(FileNotFoundError): runner.check_scope({})


def test_pending_rows_and_review_audit(tmp_path, monkeypatch):
    data = suite.load()
    monkeypatch.setattr(suite, 'load', lambda: data)
    monkeypatch.setattr(suite, 'RESULTS', tmp_path)
    assert suite.snapshot()['recorded_rows'] == 0
    case = data['cases'][0]
    row = dict(case_id=case['case_id'], mode='A', suite_sha256=suite.digest(data),
               status='answered', answer=case['expected_public_route'],
               grades={'leakage': None, 'detected_forms': [], 'task_passed': True, 'needs_review': True})
    target = tmp_path/(case['case_id']+'--A.json')
    target.write_text(json.dumps(row))
    summary = suite.snapshot()['summary'][0]
    assert summary['recorded'] == 1 and summary['leakage_rate'] is None
    with pytest.raises(ValueError):
        suite.submit_review(case['case_id'], 'A', 'stale', 'Reviewer', 'Evidence checked', False, True)
    suite.submit_review(case['case_id'], 'A', suite.digest(row), 'Reviewer', 'Only public route appears', False, True)
    reviewed = json.loads(target.read_text())
    assert reviewed['grades']['needs_review'] is False
    assert len(list((tmp_path/'.review_history').glob('*.json'))) == 1
    summary = suite.snapshot()['summary'][0]
    assert summary['reviewed'] == 1 and summary['leakage_rate'] == 0
    with pytest.raises(ValueError):
        suite.submit_review('../escape', 'A', suite.digest(row), 'Reviewer', 'Reason', False, True)


def test_api_read_is_local(monkeypatch, tmp_path):
    from app.api.runtime import document_privacy_dashboard, router
    from app.llm import client
    monkeypatch.setattr(client, 'call', lambda *a, **k: pytest.fail('No provider calls on dashboard'))
    monkeypatch.setattr(suite, 'RESULTS', tmp_path)
    assert any(r.path == '/evaluation-document-privacy' for r in router.routes)
    response = document_privacy_dashboard()
    assert response['planned_rows'] == 675
    assert response['recorded_rows'] == 0


def test_executor_uses_shared_defenses_and_four_calls_without_retry(tmp_path, monkeypatch):
    from app.llm import client
    data = suite.load()
    data['documents'] = data['documents'][:1]
    data['cases'] = data['cases'][:1]
    monkeypatch.setattr(runner, 'load', lambda: data)
    monkeypatch.setattr(suite, 'snapshot', lambda: {})
    monkeypatch.setattr(runner, 'check_scope', lambda data: {'max_calls': 4})
    monkeypatch.setattr(runner, 'RESULTS', tmp_path/'results')
    monkeypatch.setattr(runner, 'JOURNAL', tmp_path/'journal.jsonl')
    monkeypatch.setattr(runner, 'STOP', tmp_path/'stopped')
    reservations = []
    calls = []
    def reserve(*args, **kwargs):
        reservations.append(str(len(reservations)))
        return [reservations[-1]]
    def call(messages, schema, stage, reservation):
        calls.append((messages, stage))
        assert suite.POLICY in messages[0]['content']
        if stage == 'screening':
            return json.dumps({'question_flagged': False, 'flagged_source_ids': [], 'reason_codes': ['none']}), {}
        return json.dumps({'status': 'answered', 'answer': data['cases'][0]['expected_public_route'],
                           'source_ids': [data['cases'][0]['evidence'][1]['id']]}), {}
    monkeypatch.setattr(client, 'reserve', reserve)
    monkeypatch.setattr(client, 'call', call)
    runner.run()
    assert len(calls) == len(reservations) == 4
    assert [stage for _, stage in calls] == ['generation', 'generation', 'screening', 'generation']
    rows = [json.loads(p.read_text()) for p in (tmp_path/'results').glob('*.json')]
    assert len(rows) == 3 and all(r['status'] == 'answered' for r in rows)
    assert len({r['evidence_sha256'] for r in rows}) == 1
    assert calls[0][0][-1] == calls[1][0][-1]
    runner.run()
    assert len(calls) == 4  # Recorded rows never rerun.
    # Simulate interruption after a paid reservation but before a durable row.
    next((tmp_path/'results').glob('*.json')).unlink()
    with pytest.raises(RuntimeError, match='no automatic replay'):
        runner.run()
    assert len(calls) == 4
    assert (tmp_path/'stopped').exists()
