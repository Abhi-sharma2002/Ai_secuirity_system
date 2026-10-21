"""UI calls FastAPI only. Untrusted content is always displayed as plain text."""
import os
from uuid import uuid4
import httpx
import streamlit as st

BASE = os.getenv('BACKEND_URL', 'http://127.0.0.1:8000')
st.set_page_config(page_title='AI Security Document Lab', layout='wide')
st.title('AI Security Document Lab')
st.caption('Fictional employee Q&A · local single user · isolated single-turn requests')


def api(method, path, **kwargs):
    try:
        r = httpx.request(method, BASE + path, timeout=180, **kwargs)
        r.raise_for_status()
        return r.json()
    except Exception as exc:
        st.error(f'Backend request failed ({type(exc).__name__}). Start the backend and inspect its request ID/logs.')
        return None


ready = api('GET', '/ready')
if ready and not ready['live']['enabled']:
    st.info(ready['live']['reason'])
uploads, chat, results = st.tabs(['Documents', 'Ask / compare', 'Saved experiments'])
with uploads:
    st.write('UTF-8 TXT/MD, text PDF, non-macro DOCX. No OCR. Limits are enforced by the backend.')
    if ready:
        st.json(ready.get('limits', {}), expanded=False)
    with st.form('upload', clear_on_submit=True):
        files = st.file_uploader('Upload documents', type=['txt', 'md', 'pdf', 'docx'], accept_multiple_files=True)
        submit = st.form_submit_button('Upload and index')
    if submit and files:
        value = api('POST', '/documents', files=[('files', (f.name, f.getvalue(), 'application/octet-stream')) for f in files])
        if value:
            st.session_state['upload_result'] = value
    if 'upload_result' in st.session_state:
        st.json(st.session_state['upload_result'], expanded=False)
    data = api('GET', '/documents')
    for item in (data or {}).get('documents', []):
        with st.expander(f"Document | {item['status']} | {item['id']}"):
            st.text(item['filename'])
            st.text(f"Document: {item['document_id']}\nVersion: {item['id']}\nActive: {item.get('active_version')}\nSHA256: {item['sha256']}")
            for warning in item.get('warnings', []):
                st.warning(warning)
            if item.get('error'):
                st.text(item['error'])
            for block in item.get('blocks', [])[:12]:
                st.caption(f"Page {block['page']} · {block['section']}")
                st.text(block['text'][:5000])
            if item['status'] == 'needs_review':
                accept = st.checkbox('I accept incomplete text extraction and its citation limits', key='a'+item['id'])
                if st.button('Activate available text only', disabled=not accept, key='p'+item['id']):
                    api('POST', f"/versions/{item['id']}/accept-partial")
                    st.rerun()
            if item.get('active_version') == item['id'] and not item.get('deleted'):
                with st.form('replace'+item['id']):
                    replacement = st.file_uploader('Explicit replacement of this document', type=['txt','md','pdf','docx'])
                    replace = st.form_submit_button('Replace active version')
                if replace and replacement:
                    st.json(api('POST', f"/documents/{item['document_id']}/replace", params={'expected_version': item['id']}, files={'file': (replacement.name, replacement.getvalue())}))
                confirm = st.checkbox('Confirm delete this document from future retrieval', key='d'+item['id'])
                if st.button('Delete', disabled=not confirm, key='b'+item['id']):
                    api('DELETE', f"/documents/{item['document_id']}", params={'expected_version': item['id']})
                    st.rerun()
            if item.get('active_version') is None and not item.get('deleted'):
                confirm_unready = st.checkbox('Confirm delete this unready document', key='du'+item['id'])
                if st.button('Delete unready document', disabled=not confirm_unready, key='bu'+item['id']):
                    api('DELETE', f"/documents/{item['document_id']}")
                    st.rerun()
with chat:
    st.caption('Playground collection only. Benchmark administration uses the CLI.')
    with st.form('question'):
        question = st.text_area('Question', max_chars=2000)
        mode = st.selectbox('Configuration', ['A', 'B', 'C'], index=1)
        st.caption('A: ordinary RAG · B: instruction separation · C: LLM screener + B')
        submit_question = st.form_submit_button('Ask once')
    if submit_question and question.strip():
        st.session_state['answer'] = api('POST', '/chat', json={'question': question, 'mode': mode, 'request_id': str(uuid4())})
    value = st.session_state.get('answer')
    if value:
        st.write('Status:', value.get('status'))
        st.text(value.get('answer') or value.get('error', ''))
        for ref in value.get('references', []):
            if ref.get('partial_text'):
                st.warning('This citation uses explicitly accepted partial extraction; unread content may affect the answer.')
            st.text(f"{ref['filename']} · page {ref['page']} · {ref['section']}\nDocument {ref['document_id']} · version {ref['version_id']}\nSource {ref['id']}")
            st.text(ref['text'])
        with st.expander('Evidence, screening, usage and provenance'):
            st.json(value)
with results:
    runs = api('GET', '/results')
    names = (runs or {}).get('runs', [])
    if not names:
        st.info('No saved experiments. Run the evaluator CLI; no example metrics are presented as measurements.')
    else:
        name = st.selectbox('Experiment', names)
        value = api('GET', '/results/'+name)
        if value:
            st.json(value['experiment'], expanded=False)
            st.json(value['summary'])
            for row in value['results']:
                with st.expander(f"{row['case_id']} / {row['mode']} / {row['response']['status']}"):
                    st.json(row)
