"""Actual loopback API + Streamlit integration; no provider calls; processes cleaned up."""
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from uuid import uuid4
import httpx

ROOT=Path(__file__).resolve().parents[2]


def main():
    with tempfile.TemporaryDirectory() as folder:
        env={**os.environ,'PYTHONPATH':str(ROOT/'backend'),'APP_DATA_DIRECTORY':folder+'/runtime',
             'CHROMA_DB_PATH':folder+'/chroma','LIVE_LLM_ENABLED':'false','FREE_ONLY':'true',
             'HF_HUB_OFFLINE':'1','ANONYMIZED_TELEMETRY':'false','BACKEND_URL':'http://127.0.0.1:8765'}
        log=open(folder+'/servers.log','w+')
        processes=[]
        try:
            processes.append(subprocess.Popen([sys.executable,'-m','uvicorn','app.main:app','--host','127.0.0.1','--port','8765','--workers','1'],cwd=ROOT,env=env,stdout=log,stderr=log))
            processes.append(subprocess.Popen([sys.executable,'-m','streamlit','run','frontend/streamlit_app.py','--server.address','127.0.0.1','--server.port','8766','--server.headless','true','--browser.gatherUsageStats','false'],cwd=ROOT,env=env,stdout=log,stderr=log))
            for url in ['http://127.0.0.1:8765/health','http://127.0.0.1:8766/_stcore/health']:
                for _ in range(100):
                    try:
                        r=httpx.get(url,timeout=1)
                        if r.status_code==200:break
                    except httpx.HTTPError:pass
                    if any(p.poll() is not None for p in processes):
                        log.seek(0);raise RuntimeError(log.read())
                    time.sleep(.2)
                else:raise RuntimeError('Local service startup deadline exceeded')
            ready=httpx.get(env['BACKEND_URL']+'/ready').json();assert not ready['live']['enabled']
            r=httpx.post(env['BACKEND_URL']+'/documents',files={'files':('Fresh HR Policy.md',b'Annual leave entitlement is eighteen days.')},timeout=120)
            r.raise_for_status();assert r.json()['outcomes'][0]['status']=='ready',r.text
            os.environ['BACKEND_URL']=env['BACKEND_URL']
            from streamlit.testing.v1 import AppTest
            ui=AppTest.from_file(str(ROOT/'frontend/streamlit_app.py'),default_timeout=90).run()
            assert not ui.exception,[e.message for e in ui.exception]
            assert len(ui.tabs)==3
            ui.text_area[0].input('How much annual leave is available?')
            next(b for b in ui.button if b.label=='Ask once').click().run()
            assert not ui.exception,[e.message for e in ui.exception]
            assert any('Live Groq is disabled' in str(t.value) for t in ui.text)
            # Backend idempotency survives the UI read/rerun path and does not reissue generation.
            with httpx.Client(base_url=env['BACKEND_URL'],timeout=30) as api:
                query={'question':'Annual leave?','mode':'B','request_id':str(uuid4())}
                a=api.post('/chat',json=query).json();b=api.post('/chat',json=query).json()
                assert a==b and a['status']=='live_blocked'
            print(json.dumps({'api_health':True,'ui_health':True,'actual_upload_and_cpu_index':True,
                'streamlit_tabs':3,'streamlit_submit_to_actual_backend':True,'idempotency':True,
                'honest_live_blocker':True,'provider_calls':0},indent=2))
        finally:
            for process in processes:
                process.terminate()
            for process in processes:
                try:process.wait(timeout=5)
                except subprocess.TimeoutExpired:process.kill();process.wait()
            log.close()

if __name__=='__main__':main()
