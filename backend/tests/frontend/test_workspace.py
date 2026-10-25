import unittest
from pathlib import Path
from unittest.mock import patch
from streamlit.testing.v1 import AppTest


class Response:
    def __init__(self, data): self.data = data
    def raise_for_status(self): pass
    def json(self): return self.data


class WorkspaceTests(unittest.TestCase):
    def test_navigation_loads_only_selected_workspace(self):
        calls=[]
        def request(method,url,**kwargs):
            calls.append(url)
            if url.endswith('/ready'):
                return Response({'live': {'enabled':False,'reason':'Synthetic disabled'}, 'limits':{},'configuration':{'provider':'synthetic','model':'synthetic'}})
            if url.endswith('/documents'):return Response({'documents':[]})
            if url.endswith('/search'):return Response({'hits':[{'id':'synthetic-s1','filename':'fictional.txt','page':0,'text':'Synthetic leave allowance is 25 days.','version_id':'v1'}]})
            if url.endswith('/results'):return Response({'runs':[]})
            if url.endswith('/diagnostics'):return Response({'diagnostics':[]})
            raise AssertionError('Unexpected API call')
        with patch('httpx.request', side_effect=request), patch('socket.socket.connect', side_effect=AssertionError('Network forbidden')):
            app=AppTest.from_file(str(Path('frontend/streamlit_app.py').resolve())).run(timeout=15)
            self.assertFalse(app.exception)
            self.assertTrue(any(u.endswith('/documents') for u in calls))
            self.assertFalse(any(u.endswith('/results') for u in calls))
            calls.clear()
            app.sidebar.radio[0].set_value('Ask / compare').run()
            self.assertFalse(app.exception)
            self.assertFalse(any(u.endswith('/documents') for u in calls))
            self.assertEqual(len(app.selectbox),1)
            self.assertFalse(app.button[0].disabled)
            app.sidebar.radio[0].set_value('Saved experiments').run()
            self.assertFalse(app.exception)
            self.assertTrue(any(u.endswith('/results') for u in calls))
            calls.clear()
            app.sidebar.radio[0].set_value('Search evidence').run()
            app.text_input[0].set_value('What is the fictional leave allowance?')
            app.button[0].click().run()
            self.assertFalse(app.exception)
            self.assertTrue(any(u.endswith('/search') for u in calls))
            self.assertFalse(any(u.endswith('/chat') for u in calls))
            app.sidebar.radio[0].set_value('Assignment guide').run()
            self.assertFalse(app.exception)

    def test_expiry_display_uses_ist(self):
        from frontend.presentation import expiry_label
        self.assertEqual(expiry_label('2026-10-25T07:30:00+00:00'), '25 Oct 2026, 01:00:00 PM IST')
        self.assertEqual(expiry_label(None), 'Unknown expiry')
