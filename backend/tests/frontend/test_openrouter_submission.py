"""Exercise the real form with synthetic HTTP replies; never send a model request."""
from pathlib import Path
from unittest.mock import patch

import httpx
from streamlit.testing.v1 import AppTest


def application(budget, calls):
    def request(method, url, **kwargs):
        calls.append((method, url, kwargs))
        if url.endswith('/ready'):
            data = {'live': budget, 'limits': {}}
        elif url.endswith('/chat'):
            data = {'status': 'answered', 'answer': 'Synthetic form test answer.', 'mode': 'B', 'references': []}
        else:
            data = {'documents': [], 'runs': []}
        return httpx.Response(200, json=data, request=httpx.Request(method, url))
    return request


def ask_page():
    script = Path(__file__).resolve().parents[3] / 'frontend/streamlit_app.py'
    app = AppTest.from_file(str(script)).run(timeout=15)
    app.sidebar.radio[0].set_value('Ask / compare').run()
    next(r for r in app.radio if r.label == 'Document handling').set_value('openrouter').run()
    assert not app.exception
    return app


def test_ready_form_can_submit_without_checkbox_and_only_click_sends_confirmation():
    calls = []
    budget = {'enabled': True, 'mode_available': {'A': True, 'B': True, 'C': True}}
    with patch('httpx.request', side_effect=application(budget, calls)), \
         patch('socket.socket.connect', side_effect=AssertionError('Network forbidden')):
        app = ask_page()
        ask = next(b for b in app.button if b.label == 'Ask once via OpenRouter')
        assert not ask.disabled
        assert not app.checkbox
        assert any('sends your question and retrieved document passages' in c.value for c in app.caption)
        assert not any(method == 'POST' for method, _, _ in calls)
        app.run()
        assert not any(method == 'POST' for method, _, _ in calls)
        next(t for t in app.text_area if t.label == 'Question').input('Synthetic leave question')
        next(b for b in app.button if b.label == 'Ask once via OpenRouter').click().run()
        assert not app.exception
        posts = [(url, kwargs) for method, url, kwargs in calls if method == 'POST']
        assert len(posts) == 1 and posts[0][0].endswith('/chat')
        assert posts[0][1]['json']['external_processing_confirmed'] is True
        assert posts[0][1]['json']['question'] == 'Synthetic leave question'
        app.run()
        assert sum(method == 'POST' for method, _, _ in calls) == 1


def test_expired_or_unfunded_scope_keeps_external_submit_disabled():
    calls = []
    budget = {'enabled': False, 'reason': 'Synthetic scope expired',
              'mode_available': {'A': False, 'B': False, 'C': False}}
    with patch('httpx.request', side_effect=application(budget, calls)), \
         patch('socket.socket.connect', side_effect=AssertionError('Network forbidden')):
        app = ask_page()
        assert next(b for b in app.button if b.label == 'Ask once via OpenRouter').disabled
        assert not any(method == 'POST' for method, _, _ in calls)
        next(r for r in app.radio if r.label == 'Document handling').set_value('local').run()
        assert not next(b for b in app.button if b.label == 'Search locally').disabled


def test_c_requires_its_own_remaining_capacity():
    calls = []
    budget = {'enabled': True, 'mode_available': {'A': True, 'B': True, 'C': False}}
    with patch('httpx.request', side_effect=application(budget, calls)), \
         patch('socket.socket.connect', side_effect=AssertionError('Network forbidden')):
        app = ask_page()
        next(s for s in app.selectbox if s.label == 'Defense configuration').set_value('C').run()
        assert next(b for b in app.button if b.label == 'Ask once via OpenRouter').disabled
        next(s for s in app.selectbox if s.label == 'Defense configuration').set_value('A').run()
        assert not next(b for b in app.button if b.label == 'Ask once via OpenRouter').disabled
        assert not any(method == 'POST' for method, _, _ in calls)
