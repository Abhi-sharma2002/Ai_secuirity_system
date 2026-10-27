"""Record a local browser walkthrough of saved live results; no provider calls."""
import argparse
import base64
import csv
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / 'backend')]
from frontend.redaction import mask_text


def slides():
    rows = list(csv.DictReader((ROOT / 'results/records.csv').open()))
    summary = list(csv.DictReader((ROOT / 'results/summary.csv').open()))
    cases = json.loads((ROOT / 'backend/benchmark_v3/manifest.json').read_text())['cases']
    by_case = {c['case_id']: c for c in cases}
    complete = len(rows) == len(cases) * 3
    result = [{'title': 'AI Security Document Lab', 'subtitle': 'Recorded walkthrough of saved Azure gpt-5-mini responses',
               'lines': [f'{len(rows)} / {len(cases) * 3} A/B/C records saved',
                         'A: grounded baseline | B: instruction separation | C: screening + output checks',
                         'Actual saved responses; this recording makes no new LLM requests.',
                         'All case/mode rows recorded; human review is still required' if complete else 'Partial comparison: missing rows remain unavailable',
                         f"Operational errors: {sum(bool(r['error']) for r in rows)}; judgments awaiting human review: {sum(r['needs_review']=='true' for r in rows)}."]}]
    benign = next((r for r in rows if not by_case[r['case_id']]['adversarial'] and not r['error'] and r['mode'] == 'A'), None)
    if benign:
        result.append({'title': '1. Normal question', 'subtitle': benign['case_id'] + ' / A',
                       'lines': ['Question: ' + benign['query'], 'Actual answer: ' + benign['answer'],
                                 'Citations: ' + benign['sources'], 'Task passed (automated): ' + benign['task_passed']]})
    attack = next((r for r in rows if r['case_id'] == 'final-21' and r['mode'] == 'A' and r['attack_succeeded'] == 'true' and not r['error']), None)
    if attack is None:
        attack = next((r for r in rows if r['mode'] == 'A' and r['attack_succeeded'] == 'true' and not r['error']), None)
    if attack is None:
        attack = next((r for r in rows if r['mode'] == 'A' and by_case[r['case_id']]['adversarial'] and not r['error']), None)
    if attack is None:
        attack = next((r for r in rows if r['mode'] == 'A' and by_case[r['case_id']]['adversarial']), None)
    if attack:
        for mode in 'ABC':
            row = next((r for r in rows if r['case_id'] == attack['case_id'] and r['mode'] == mode), None)
            if not row:
                continue
            result.append({'title': {'A': '2. Injection against baseline', 'B': '3. Same case: instruction separation',
                                     'C': '4. Same case: screening + output checks'}[mode],
                           'subtitle': row['case_id'] + ' / ' + mode,
                           'lines': ['Question: ' + row['query'], 'Actual answer: ' + row['answer'],
                                     'Attack succeeded (automated): ' + (row['attack_succeeded'] or 'pending'),
                                     'Task passed (automated): ' + (row['task_passed'] or 'pending'),
                                     'Operational error: ' + (row['error'] or 'none'),
                                     'Human ambiguity review needed: ' + row['needs_review']]})
    if benign:
        defended = next((r for r in rows if r['case_id'] == benign['case_id'] and r['mode'] == 'C'), None)
        if defended:
            result.append({'title': '5. Benign task preserved with defense', 'subtitle': defended['case_id'] + ' / C',
                           'lines': ['Question: ' + defended['query'], 'Actual answer: ' + defended['answer'],
                                     'Task passed (automated): ' + defended['task_passed'],
                                     'Citations: ' + defended['sources']]})
    def percentage(value):
        return f'{float(value):.1%}' if value else 'N/A'
    result.append({'title': '6. Measured comparison', 'subtitle': 'Rates exclude errors and unresolved semantic judgments',
                   'lines': [f"{s['mode']}: ASR {percentage(s['asr_all'])} ({s['asr_all_numerator']}/{s['asr_all_denominator']}); "
                             f"benign success {percentage(s['benign_task_success'])}; false positives {percentage(s['pdf_false_positive_rate'])}; "
                             f"human quality {s['mean_quality'] or 'N/A'}; mean time {float(s['mean_latency_s']):.2f}s."
                             for s in summary] + ['Full formulas and denominators: docs/REPORT.md and results/summary.csv',
                                                   'Display masking is not scored as model resistance.',
                                                   'Human answer-quality scores remain pending until a person supplies them.']})
    return [{**s, 'lines': [mask_text(line) for line in s['lines']]} for s in result]


HTML = r'''<!doctype html><meta charset="utf-8"><title>Saved live comparison demo</title>
<style>body{margin:0;background:#101827}canvas{display:block;margin:auto;max-width:100vw}</style>
<canvas id="view" width="1280" height="720"></canvas><script>
const slides = __SLIDES__;
const canvas=document.getElementById('view'),ctx=canvas.getContext('2d');
function wrap(text,y){ctx.font='22px sans-serif';let line='';for(const word of text.split(/\s+/)){
 if(ctx.measureText(line+word).width>1120){ctx.fillText(line,70,y);y+=31;line='';if(y>620){ctx.fillText('… See saved records for the complete text.',70,y);return 660;}}
 line+=word+' ';}ctx.fillText(line,70,y);return y+43;}
function draw(i){let s=slides[i];ctx.fillStyle='#101827';ctx.fillRect(0,0,1280,720);
ctx.fillStyle='#57d8b0';ctx.font='18px sans-serif';ctx.fillText('AI SECURITY / SAVED LIVE EVIDENCE',70,50);
ctx.fillStyle='#ffffff';ctx.font='bold 37px sans-serif';ctx.fillText(s.title,70,112);
ctx.fillStyle='#aebcd0';ctx.font='20px sans-serif';ctx.fillText(s.subtitle,70,151);
ctx.fillStyle='#eef3fb';let y=211;for(const line of s.lines){if(y>620)break;y=wrap(line,y);}
ctx.fillStyle='#aebcd0';ctx.font='16px sans-serif';ctx.fillText('Saved-response replay • synthetic documents • private values masked',70,688);
ctx.fillText((i+1)+' / '+slides.length,1165,688);}
draw(0);
window.record=async()=>{const chunks=[];const stream=canvas.captureStream(12);
const recorder=new MediaRecorder(stream,{mimeType:'video/webm;codecs=vp8',videoBitsPerSecond:1600000});
const done=new Promise(resolve=>recorder.onstop=resolve);recorder.ondataavailable=e=>{if(e.data.size)chunks.push(e.data)};
recorder.start(200);for(let i=0;i<slides.length;i++){draw(i);await new Promise(r=>setTimeout(r,5000));}
recorder.stop();await done;stream.getTracks().forEach(t=>t.stop());
return await new Promise(resolve=>{const reader=new FileReader();reader.onload=()=>{window.recordedData=reader.result;resolve(reader.result.split(',')[1]);};reader.readAsDataURL(new Blob(chunks,{type:'video/webm'}));});};
</script>'''


def main():
    import websocket
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / 'docs/demo/azure-live-comparison-20261026.webm')
    output = parser.parse_args().output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        raise SystemExit('Recording already exists; preserve it before recording another.')
    data = json.dumps(slides(), ensure_ascii=True).replace('<', '\\u003c').replace('>', '\\u003e')
    html = output.with_suffix('.html')
    html.write_text(HTML.replace('__SLIDES__', data))
    chrome = shutil.which('google-chrome')
    if not chrome:
        raise SystemExit('A local Chrome browser is required for recording.')
    with tempfile.TemporaryDirectory(prefix='security-demo-browser-', ignore_cleanup_errors=True) as profile:
        with (Path(profile) / 'browser.log').open('w') as log:
            process = subprocess.Popen([chrome, '--headless=new', '--disable-gpu', '--no-first-run',
                '--disable-background-networking', '--disable-sync', '--disable-extensions',
                '--remote-debugging-address=127.0.0.1', '--remote-debugging-port=0',
                '--remote-allow-origins=http://localhost', '--user-data-dir=' + profile, 'about:blank'], stdout=log, stderr=log)
            try:
                active = Path(profile) / 'DevToolsActivePort'
                for _ in range(100):
                    if active.exists(): break
                    if process.poll() is not None: raise RuntimeError('Local browser exited before readiness')
                    time.sleep(.1)
                port = active.read_text().splitlines()[0]
                import urllib.request
                targets = json.loads(urllib.request.urlopen('http://127.0.0.1:' + port + '/json').read())
                ws = websocket.create_connection(next(t['webSocketDebuggerUrl'] for t in targets if t['type']=='page'),
                                                 origin='http://localhost', timeout=90)
                sequence = 0
                def call(method, params):
                    nonlocal sequence
                    sequence += 1
                    ws.send(json.dumps({'id':sequence,'method':method,'params':params}))
                    while True:
                        response=json.loads(ws.recv())
                        if response.get('id')==sequence:
                            if 'error' in response: raise RuntimeError('Local browser recording command failed')
                            return response.get('result',{})
                call('Page.navigate', {'url':html.as_uri()})
                for _ in range(100):
                    ready=call('Runtime.evaluate',{'expression':'typeof window.record','returnByValue':True})
                    if ready.get('result',{}).get('value')=='function': break
                    time.sleep(.1)
                result=call('Runtime.evaluate',{'expression':'window.record()','awaitPromise':True,'returnByValue':True})
                if 'exceptionDetails' in result: raise RuntimeError('Browser recording failed')
                video=base64.b64decode(result['result']['value'])
                if len(video)<1000 or not video.startswith(b'\x1aE\xdf\xa3'): raise RuntimeError('Invalid WebM output')
                output.write_bytes(video)
                playback=call('Runtime.evaluate',{'expression':"""new Promise((resolve,reject)=>{let v=document.createElement('video');v.muted=true;v.onloadeddata=()=>resolve({width:v.videoWidth,height:v.videoHeight,ready:v.readyState});v.onerror=()=>reject(new Error('Playback failed'));v.src=window.recordedData;v.load();})""",'awaitPromise':True,'returnByValue':True})
                dimensions=playback.get('result',{}).get('value',{})
                if dimensions.get('width')!=1280 or dimensions.get('height')!=720:
                    raise RuntimeError('Recorded video could not be decoded at the expected dimensions')
                ws.close()
                print(json.dumps({'recording':str(output),'bytes':len(video),
                                  'slides':len(slides()),'provider_calls':0,'format':'WebM/VP8','playback_verified':True}))
            finally:
                process.terminate()
                try: process.wait(timeout=10)
                except subprocess.TimeoutExpired: process.kill();process.wait()


if __name__=='__main__': main()
