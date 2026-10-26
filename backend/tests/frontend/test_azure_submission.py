"""Azure-selected UI routing with synthetic HTTP replies and no real provider I/O."""
from unittest.mock import patch

from backend.tests.frontend.test_openrouter_submission import application, ask_page


def test_azure_selected_form_labels_and_submission_are_provider_aware():
    calls=[]
    capacity={'enabled':True, 'mode_available':{'A':True,'B':True,'C':True}}
    with patch('httpx.request', side_effect=application(capacity,calls,provider='azure_openai')), \
         patch('socket.socket.connect',side_effect=AssertionError('Network forbidden')):
        app=ask_page('azure_openai')
        assert any(b.label=='Ask once via Azure OpenAI' for b in app.button)
        assert not any(b.label=='Ask once via OpenRouter' for b in app.button)
        assert any('Azure OpenAI' in item.value for item in app.caption)
        assert all(method=='GET' for method,_,_ in calls)
        next(t for t in app.text_area if t.label=='Question').input('Synthetic leave question')
        next(b for b in app.button if b.label=='Ask once via Azure OpenAI').click().run()
        assert not app.exception
        posts=[(url,kwargs) for method,url,kwargs in calls if method=='POST']
        assert len(posts)==1 and posts[0][0].endswith('/chat')
        assert posts[0][1]['json']['external_processing_confirmed'] is True
        app.run()
        assert sum(method=='POST' for method,_,_ in calls)==1


def test_azure_missing_configuration_stays_disabled_but_local_search_available():
    calls=[]
    capacity={'enabled':False, 'reason':'Azure configuration incomplete',
              'mode_available':{'A':False,'B':False,'C':False}}
    with patch('httpx.request',side_effect=application(capacity,calls,provider='azure_openai')), \
         patch('socket.socket.connect',side_effect=AssertionError('Network forbidden')):
        app=ask_page('azure_openai')
        assert next(b for b in app.button if b.label=='Ask once via Azure OpenAI').disabled
        next(r for r in app.radio if r.label=='Document handling').set_value('local').run()
        assert not next(b for b in app.button if b.label=='Search locally').disabled
        assert all(method=='GET' for method,_,_ in calls)


def test_compare_click_includes_explicit_processing_confirmation():
    calls=[]
    capacity={'enabled':True,'remaining_calls':4,'remaining_reserved_tokens':128000,
              'expires_at':'2099-01-01T00:00:00Z'}
    with patch('httpx.request',side_effect=application(capacity,calls,provider='azure_openai')), \
         patch('socket.socket.connect',side_effect=AssertionError('Network forbidden')):
        app=ask_page('azure_openai')
        next(t for t in app.text_area if t.label=='Benign comparison question').input('Synthetic comparison')
        next(b for b in app.button if b.label=='Compare once — up to 4 calls').click().run()
        assert not app.exception
        posts=[kwargs for method,url,kwargs in calls if method=='POST' and url.endswith('/compare')]
        assert len(posts)==1 and posts[0]['json']['external_processing_confirmed'] is True
