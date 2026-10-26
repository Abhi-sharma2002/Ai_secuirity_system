"""The Ask result must not append arbitrary source text, even inside expanders."""
from copy import deepcopy
import json
from pathlib import Path
from unittest.mock import patch

import httpx
import pytest
from streamlit.testing.v1 import AppTest

from frontend.presentation import answer_view, comparison_view

ANSWER = 'Receipts are required above the company limit.'
# Ordinary text that no secret regex would mask: withholding must be structural.
UNRELATED = 'The cafeteria serves soup on Thursdays and the bicycle room is downstairs.'
RAW = {'mode': 'B', 'status': 'answered', 'answer': ANSWER,
       'references': [{'filename': 'policy.txt', 'page': 0, 'section': 'text',
                       'id': 'internal-source-id', 'text': UNRELATED}],
       'candidate_evidence': [{'text': UNRELATED}], 'supplied_evidence': [{'text': UNRELATED}],
       'screening': {'reason': UNRELATED}, 'calls': [{'raw': UNRELATED}]}


def test_answer_and_comparison_exports_exclude_full_evidence_without_changing_records():
    before = deepcopy(RAW)
    view = answer_view(RAW)
    comparison = comparison_view({'status': 'completed', 'initial_evidence': UNRELATED,
                                  'results': {mode: {**RAW, 'mode': mode} for mode in 'ABC'}})
    assert view['answer'] == ANSWER
    assert view['references'] == [{'filename': 'policy.txt', 'page': 0, 'section': 'text'}]
    assert UNRELATED not in json.dumps(view)
    assert UNRELATED not in json.dumps(comparison)
    assert 'internal-source-id' not in json.dumps(comparison)
    assert set(comparison['results']) == set('ABC')
    assert RAW == before


@pytest.mark.parametrize('mode', list('ABC'))
@pytest.mark.parametrize('extension', ['txt', 'pdf'])
def test_ask_renders_answer_and_citation_without_any_source_body_or_audit(mode, extension):
    requests = []
    def request(method, url, **kwargs):
        requests.append(method)
        data = ({'live': {'enabled': False, 'reason': 'Synthetic offline test'}, 'limits': {}}
                if url.endswith('/ready') else {'documents': []})
        return httpx.Response(200, json=data, request=httpx.Request(method, url))
    raw = deepcopy(RAW)
    raw['mode'] = mode
    raw['references'][0].update(filename='policy.' + extension, page=1 if extension == 'pdf' else 0)
    script = Path(__file__).resolve().parents[3] / 'frontend/streamlit_app.py'
    with patch('httpx.request', side_effect=request), \
         patch('socket.socket.connect', side_effect=AssertionError('Network forbidden')):
        app = AppTest.from_file(str(script))
        app.session_state['answer'] = deepcopy(raw)
        app.run(timeout=15)
        app.sidebar.radio[0].set_value('Ask / compare').run()
        assert not app.exception
        rendered = '\n'.join(str(item.value) for kind in ('text', 'caption', 'json') for item in app.get(kind))
        assert ANSWER in rendered and 'Source: policy.' + extension in rendered
        assert UNRELATED not in rendered
        assert 'internal-source-id' not in rendered
        assert not app.json
        assert not any('Source excerpt' in item.label or 'Evidence, screening' in item.label for item in app.expander)
        assert app.session_state['answer'] == raw
        assert all(method == 'GET' for method in requests)
