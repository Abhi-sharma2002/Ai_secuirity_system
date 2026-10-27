"""Actual metrics UI with labeled synthetic replies; sockets are forbidden."""
from copy import deepcopy
from io import BytesIO
from pathlib import Path
from unittest.mock import patch

import httpx
from PIL import Image
from streamlit.testing.v1 import AppTest

from app.evaluation import simple_dashboard as dashboard, simple_reporting as report
from app.evaluation.simple_config import load_config
from backend.tests.evaluation.test_simple_reporting import DATA, BENIGN, ATTACKS, row
from frontend.presentation import evaluation_metric_rows


def payload(rows=()):
    return {'status': 'partial' if rows else 'no_records', 'counts': {
        'recorded': len(rows), 'expected': len(DATA['cases']) * 3,
        'missing': len(DATA['cases']) * 3 - len(rows), 'errors': 0,
        'needs_review': 0, 'quality_reviewed': 0},
        'summary': report.summarize(rows, DATA), 'configuration': load_config(),
        'dataset': {'cases': len(DATA['cases']), 'documents': len(DATA['fixtures'])},
        'origin': 'synthetic UI test only', 'records': list(rows), 'notes': ['Errors are excluded from rates.'],
        'definitions': [dict(zip(('key', 'metric', 'formula', 'better', 'kind'), d)) for d in dashboard.DEFINITIONS],
        'charts_current': False, 'artifacts': [], 'provider_execution_enabled': False}


def application(data, calls):
    def request(method, url, **kwargs):
        calls.append((method, url))
        value = data if url.endswith('/evaluation-v3') else (
            {'live': {'enabled': False, 'reason': 'Synthetic offline test'}, 'limits': {}}
            if url.endswith('/ready') else {'documents': []})
        return httpx.Response(200, json=value, request=httpx.Request(method, url))
    return request


def metrics_page():
    script = Path(__file__).resolve().parents[3] / 'frontend/streamlit_app.py'
    app = AppTest.from_file(str(script)).run(timeout=15)
    app.sidebar.radio[0].set_value('Metrics / evaluation').run()
    assert not app.exception
    return app


def test_every_metric_has_na_or_explicit_denominators():
    data = payload()
    rows = evaluation_metric_rows(data['summary'], data['definitions'])
    assert len(rows) == len(dashboard.DEFINITIONS)
    assert all(r['A'].startswith('N/A') for r in rows)
    data = payload([row(ATTACKS[0], attack_succeeded='true'), row(BENIGN[0], 'C')])
    rows = evaluation_metric_rows(data['summary'], data['definitions'])
    by_name = {r['Metric']: r for r in rows}
    assert by_name['Attack success — all']['A'] == '100.0% (1/1)'
    assert by_name['Attack success — all']['B'] == 'N/A'
    assert by_name['False positive rate']['A'] == 'N/A (C only)'


def test_empty_metrics_page_explains_na_all_metrics_and_exclusions():
    calls = []
    with patch('httpx.request', side_effect=application(payload(), calls)), \
         patch('socket.socket.connect', side_effect=AssertionError('Network forbidden')):
        app = metrics_page()
        assert any('No live v3 evaluation records' in item.value for item in app.info)
        frame = app.dataframe[0].value
        assert set(frame.columns) == {'Metric', 'A', 'B', 'C'}
        assert len(frame) == len(dashboard.DEFINITIONS)
        assert any('Errors are excluded' in item.value for item in app.text)
        assert all(method == 'GET' for method, _ in calls)
        assert not any(url.endswith('/evaluation-v3') for _, url in calls[:2])


def test_all_metric_artifact_names_are_requested_only_on_metrics_page():
    data, calls, downloads = payload(), [], []
    data.update(charts_current=True, artifacts=list(dashboard.CHARTS))
    output = BytesIO()
    Image.new('RGB', (4, 4)).save(output, format='PNG')
    def get(url, **kwargs):
        downloads.append(url.rsplit('/', 1)[-1])
        return httpx.Response(200, content=output.getvalue())
    with patch('httpx.request', side_effect=application(data, calls)), \
         patch('httpx.get', side_effect=get), \
         patch('socket.socket.connect', side_effect=AssertionError('Network forbidden')):
        app = metrics_page()
        assert downloads == list(dashboard.CHARTS)
        assert len(app.get('download_button')) == 7
        assert all(method == 'GET' for method, _ in calls)


def test_case_inspector_filters_errors_and_preserves_input():
    rows = [row(), row(ATTACKS[0], 'C', error='Synthetic provider timeout')]
    data, calls = payload(rows), []
    before = deepcopy(data)
    with patch('httpx.request', side_effect=application(data, calls)), \
         patch('socket.socket.connect', side_effect=AssertionError('Network forbidden')):
        app = metrics_page()
        next(s for s in app.selectbox if s.label == 'Record status').set_value('Errors').run()
        selector = next(s for s in app.selectbox if s.label == 'Inspect case / configuration')
        assert selector.options == [rows[1]['case_id'] + ' / C']
        assert data == before
        assert all(method == 'GET' for method, _ in calls)


def test_same_case_comparison_shows_defenses_docs_and_missing_without_provider_calls():
    from app.evaluation.case_comparison import compare_cases, DEFENSES
    case = BENIGN[0]
    rows = [row(case, 'A', answer='Observed answer A'),
            row(case, 'C', answer='', error='Synthetic schema failure')]
    data, calls = payload(rows), []
    data.update(case_comparisons=compare_cases(rows, DATA), defense_mechanisms=DEFENSES)
    before = deepcopy(data)
    with patch('httpx.request', side_effect=application(data, calls)), \
         patch('socket.socket.connect', side_effect=AssertionError('Network forbidden')):
        app = metrics_page()
        assert any('Grounded baseline' in item.value for item in app.markdown)
        assert any('Instruction separation' in item.value for item in app.markdown)
        assert any('Screening and output checks' in item.value for item in app.markdown)
        assert any('Input documents:' in item.value for item in app.text)
        assert any('B · Not run' in item.value for item in app.markdown)
        assert any('C · Operational error' in item.value for item in app.markdown)
        assert any('Observed answer A' in item.value for item in app.text)
        selector = next(s for s in app.selectbox if s.label == 'Test case for A/B/C comparison')
        assert len(selector.options) == 47
        assert data == before
        assert all(method == 'GET' for method, _ in calls)


def test_human_quality_form_requires_explicit_submit_and_preserves_answer_binding():
    target = row()
    data, calls, submitted = payload([target]), [], []
    digest = report.row_digest(target)
    data['review_hashes'] = {target['case_id'] + '/A': digest}
    data['case_metadata'] = {target['case_id']: {'adversarial': False, 'supporting_quotes': ['Synthetic evidence']}}
    read = application(data, calls)
    def request(method, url, **kwargs):
        if method == 'POST':
            submitted.append((url, kwargs['json']))
            return httpx.Response(200, json={'saved': True}, request=httpx.Request(method, url))
        return read(method, url, **kwargs)
    with patch('httpx.request', side_effect=request), patch('socket.socket.connect', side_effect=AssertionError('Network forbidden')):
        app = metrics_page()
        assert not submitted
        next(b for b in app.button if b.label == 'Save my quality review').click().run()
        assert not submitted
        next(t for t in app.text_input if t.label == 'Your name (human reviewer)').input('SYNTHETIC HUMAN TEST INPUT')
        next(s for s in app.selectbox if s.label == 'Answer quality').set_value(3)
        next(s for s in app.selectbox if s.label.startswith('Do you agree with the automatic task grade')).set_value('Yes')
        next(b for b in app.button if b.label == 'Save my quality review').click().run()
        assert not app.exception
        assert len(submitted) == 1
        url, body = submitted[0]
        assert url.endswith('/evaluation-v3/quality-review')
        assert body['record_sha256'] == digest
        assert body['quality_0_4'] == 3 and body['task_correct'] is True
        assert body['attack_correct'] is None
