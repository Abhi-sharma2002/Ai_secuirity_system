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
    assert rows[0]['A'] == '100.0% (1/1)'
    assert rows[0]['B'] == 'N/A'
    assert rows[5]['A'] == 'N/A (C only)'


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


def test_all_six_real_artifact_names_are_requested_only_on_metrics_page():
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
        assert len(app.get('download_button')) == 6
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
