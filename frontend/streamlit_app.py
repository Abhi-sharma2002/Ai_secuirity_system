"""UI calls FastAPI only. Untrusted content is always displayed as plain text."""
import os
import json
from uuid import uuid4
import httpx
import streamlit as st
from frontend.error_messages import describe_error
from frontend.presentation import metric_rows, page_label, expiry_label, answer_preview, answer_view, comparison_view
from frontend.redaction import artifact_preview

BASE = os.getenv('BACKEND_URL', 'http://127.0.0.1:8000')
st.set_page_config(page_title='AI Security Document Lab', layout='wide')
st.title('AI Security Document Lab')
st.caption('Local-first employee-document Q&A · single user · isolated single-turn requests')


def api(method, path, **kwargs):
    try:
        r = httpx.request(method, BASE + path, timeout=180, **kwargs)
        r.raise_for_status()
        return r.json()
    except httpx.TimeoutException:
        st.error('The local request timed out. Processing may still be running. Refresh Documents to inspect its state before submitting again; no automatic retry was made.')
        return None
    except httpx.HTTPStatusError as exc:
        st.error(f'Backend rejected this request (HTTP {exc.response.status_code}). Check the file limits and document state. No automatic retry was made.')
        return None
    except Exception as exc:
        st.error(f'Backend request failed ({type(exc).__name__}). Start the backend and inspect its request ID/logs.')
        return None


def artifact_bytes(run, filename):
    try:
        response = httpx.get(BASE+'/results/'+run+'/artifacts/'+filename, timeout=10)
        return response.content if response.status_code == 200 else None
    except httpx.HTTPError:
        st.warning('Result file unavailable. Refresh after checking backend health; no model request was made.')
        return None


ready = api('GET', '/ready')
if ready and not ready['live']['enabled']:
    st.warning(ready['live']['reason'])
    missing = ready.get('configuration', {}).get('missing_configuration', [])
    if missing:
        st.info('Configure the backend root .env: ' + ', '.join(missing))
if ready and 'remaining_calls' in ready['live']:
    live_status = ready['live']
    expiry = live_status.get('expires_at')
    expiry_text = ('No time expiry' if expiry is None and 'expires_at' in live_status
                   else 'Approval expires ' + expiry_label(expiry))
    st.caption(f"Remaining: {live_status['remaining_calls']} provider calls · {live_status['remaining_reserved_tokens']} local units · {expiry_text}")
page = st.sidebar.radio('Workspace', ['Documents', 'Search evidence', 'Ask / compare', 'Metrics / evaluation', 'Saved experiments', 'Assignment guide'])
if ready:
    config = ready.get('configuration', {})
    st.caption('Provider: ' + str(config.get('provider', 'unknown')) + ' · Model: ' + str(config.get('model', 'unknown')))
selected_provider = (ready or {}).get('configuration', {}).get('provider', 'azure_openai')
provider_name = 'OpenRouter' if selected_provider == 'openrouter' else 'Azure OpenAI'
external_mode = 'openrouter' if selected_provider == 'openrouter' else 'azure_openai'
st.info(
    'Documents are parsed, indexed, and searched locally. Local-only mode never calls a model and returns matching evidence. '
    f'{provider_name} mode sends your question and retrieved passages to the external provider for answering (and, in C, screening). '
    'Use it only for content you are authorized to send. Files, indexes, and request results persist locally; this app does not provide encryption, access control, or secure-erasure guarantees. '
    'A is the baseline; B adds instruction separation; C adds model-based screening and a payment-card-number check. These are experimental defenses, not production secrecy controls.'
)
if page == 'Documents':
    st.write('UTF-8 TXT/MD, text PDF, non-macro DOCX. No OCR. Limits are enforced by the backend.')
    if ready:
        st.json(ready.get('limits', {}), expanded=False)
    st.caption('Up to 5 files per upload. The first upload may take longer while the cached CPU embedding model loads. Scanned/image-only PDFs need text extraction outside this app; OCR is not supported.')
    file_limit_bytes = (ready or {}).get('limits', {}).get('max_file_bytes', 5 * 1024 * 1024)
    file_limit_mb = max(1, (file_limit_bytes + 1024**2 - 1) // 1024**2)
    with st.form('upload', clear_on_submit=True):
        files = st.file_uploader('Upload documents', type=['txt', 'md', 'pdf', 'docx'], accept_multiple_files=True, max_upload_size=file_limit_mb)
        submit = st.form_submit_button('Upload and index')
    if submit and files:
        limit = (ready or {}).get('limits', {}).get('max_file_bytes', 5 * 1024 * 1024)
        if len(files) > 5 or any(f.size > limit for f in files):
            st.error(f'Choose at most 5 files, each no larger than {limit / 1024**2:g} MB.')
            value = None
        else:
            with st.spinner('Uploading, extracting text, creating chunks and indexing locally. Please wait; do not submit again.'):
                value = api('POST', '/documents', files=[('files', (f.name, f.getvalue(), 'application/octet-stream')) for f in files])
        if value:
            st.session_state['upload_result'] = value
    if 'upload_result' in st.session_state:
        upload_preview = answer_preview(st.session_state['upload_result'])
        for outcome in upload_preview.get('outcomes', []):
            st.text(str(outcome.get('filename', 'Document')) + ' — ' + str(outcome.get('status', 'unknown')))
            if outcome.get('error'):
                st.warning(outcome['error'])
        with st.expander('Upload details'):
            st.json(upload_preview, expanded=False)
    show_deleted = st.checkbox('Show deleted documents', value=False,
                               help='Deleted documents are excluded from future retrieval. This only changes the history view; it does not delete or restore anything.')
    data = api('GET', '/documents', params={'include_deleted': show_deleted})
    documents = (data or {}).get('documents', [])
    if not documents:
        if show_deleted:
            st.info('No documents match this view.')
        else:
            st.info('No active documents yet. Deleted document history is hidden; use “Show deleted documents” to view it.')
    for item in answer_preview(documents):
        with st.expander(f"{item['filename']} | {item['status']}"):
            st.text(item['filename'])
            st.text(f"Document: {item['document_id']}\nVersion: {item['id']}\nActive: {item.get('active_version')}\nSHA256: {item['sha256']}")
            for warning in item.get('warnings', []):
                st.warning(warning)
            if item.get('error'):
                st.text(item['error'])
            for block in item.get('blocks', [])[:12]:
                st.caption(f"{page_label(block['page'])} · {block['section']}")
                st.text(block['text'][:5000])
            if item['status'] == 'needs_review':
                accept = st.checkbox('I accept incomplete text extraction and its citation limits', key='a'+item['id'])
                if st.button('Activate available text only', disabled=not accept, key='p'+item['id']):
                    api('POST', f"/versions/{item['id']}/accept-partial")
                    st.rerun()
            if item.get('active_version') == item['id'] and not item.get('deleted'):
                with st.form('replace'+item['id']):
                    replacement = st.file_uploader('Explicit replacement of this document', type=['txt','md','pdf','docx'], max_upload_size=file_limit_mb)
                    replace = st.form_submit_button('Replace active version')
                if replace and replacement:
                    with st.spinner('Replacing and indexing the new version locally…'):
                        st.json(answer_preview(api('POST', f"/documents/{item['document_id']}/replace", params={'expected_version': item['id']}, files={'file': (replacement.name, replacement.getvalue())})))
                confirm = st.checkbox('Confirm delete this document from future retrieval', key='d'+item['id'])
                if st.button('Delete', disabled=not confirm, key='b'+item['id']):
                    api('DELETE', f"/documents/{item['document_id']}", params={'expected_version': item['id']})
                    st.rerun()
            if item.get('active_version') is None and not item.get('deleted'):
                confirm_unready = st.checkbox('Confirm delete this unready document', key='du'+item['id'])
                if st.button('Delete unready document', disabled=not confirm_unready, key='bu'+item['id']):
                    api('DELETE', f"/documents/{item['document_id']}")
                    st.rerun()
if page == 'Search evidence':
    st.subheader('Search active document evidence locally')
    st.caption('Uses the cached CPU embedding model and local Chroma. No answering call or allowance is required.')
    with st.form('search-evidence'):
        search_question = st.text_input('What fact are you looking for?', max_chars=2000)
        search_submit = st.form_submit_button('Search locally')
    if search_submit and search_question.strip():
        with st.spinner('Searching active document versions locally…'):
            st.session_state['search_result'] = api('POST', '/search', json={
                'question': search_question, 'mode': 'A', 'request_id': str(uuid4())})
    found = answer_preview(st.session_state.get('search_result'))
    if found is not None:
        st.caption('Saved search result. Search again after replacing or deleting documents.')
        hits = found.get('hits', [])
        if not hits:
            st.info('No active evidence found. Check the Documents lifecycle state and try a more specific question.')
        for hit in hits:
            with st.expander(str(hit.get('filename', 'Document')) + ' · ' + page_label(hit.get('page'))):
                st.text(hit.get('text', ''))
                st.caption('Source: ' + str(hit.get('id')) + ' · Version: ' + str(hit.get('version_id')))
                if hit.get('partial_text'):
                    st.warning('This is explicitly accepted partial extraction.')
if page == 'Assignment guide':
    st.subheader('Assignment workflow')
    st.write('1. Upload only documents you are authorized to process; parsing, indexing, storage, and local evidence search stay on this machine.')
    st.write(f'2. Use local-only mode to inspect matching sources without a model call, or choose {provider_name} and click Ask to send the question and matching passages to the provider.')
    st.write('3. A is the baseline; B separates instructions; C screens inputs and checks for payment-card-number patterns. None guarantees protection from prompt injection or disclosure.')
    st.write('4. Run controlled evaluation only under a separate approved benchmark scope. Use identical initial evidence, model and answering settings across A/B/C.')
    st.write('5. Review actual responses against expected answers and attack objectives. Provider errors and retrieval misses are not successful defenses.')
    st.write('6. Open Saved experiments for grouped A/B/C responses, metric denominators, charts and review-template downloads.')
    st.write('7. Demonstrate a supported benign answer, the same attack against A/B/C, benign task preservation, and actual measured trade-offs.')
    st.info('The historical app dataset has 42 documents and 42 cases. The separate v3 comparison uses backend/benchmark_v3 and the local scripts documented in README.md. Its live checks are deferred. Historical observations do not verify effectiveness for a newly selected deployment.')
    st.caption('Metrics: ASR = reviewed successful attacks / eligible reviewed attacks; benign success = correct reviewed benign tasks / eligible reviewed benign tasks; false positives = benign cases flagged or blocked / eligible benign cases. Quality uses the approved 0–4 rubric. Latency and reported token usage remain separate from local reservation units.')
if page == 'Ask / compare':
    st.caption('Interactive capacity is for benign questions; benchmark attacks belong to separately authorized evaluation. Never resend a prohibited provider-blocked payload.')
    mode = st.selectbox('Defense configuration', ['A', 'B', 'C'], index=1,
                        format_func=lambda value: {'A': 'A — Baseline RAG', 'B': 'B — Instruction separation', 'C': 'C — LLM screening + instruction separation'}[value])
    st.caption('Choose a defense before asking. A: baseline · B: separation · C: screening + separation')
    processing_mode = st.radio(
        'Document handling',
        ['local', external_mode],
        format_func=lambda value: (
            'Local-only — search evidence, no model call' if value == 'local'
            else provider_name + ' — send question and retrieved passages to the provider'
        ),
    )
    with st.form('question'):
        question = st.text_area('Question', max_chars=2000)
        live_status = (ready or {}).get('live', {})
        can_use_external = live_status.get('mode_available', {}).get(mode, live_status.get('enabled', False))
        if processing_mode != 'local':
            st.caption(f'Clicking “Ask once via {provider_name}” sends your question and retrieved document passages to {provider_name} for processing.')
            if not can_use_external:
                st.info(live_status.get('reason') or 'Insufficient capacity for this configuration. A/B require 1 call; C requires 2.')
        can_ask = processing_mode == 'local' or can_use_external
        submit_question = st.form_submit_button('Search locally' if processing_mode == 'local' else 'Ask once via ' + provider_name, disabled=not can_ask)
    if submit_question and can_ask and question.strip():
        if processing_mode == 'local':
            with st.spinner('Searching local evidence. No model request will be made.'):
                st.session_state['local_search'] = api('POST', '/search', json={
                    'question': question, 'mode': mode, 'request_id': str(uuid4())})
            st.session_state.pop('answer', None)
        else:
            with st.spinner('Retrieving evidence and requesting an answer. No automatic retries.'):
                st.session_state['answer'] = api('POST', '/chat', json={
                    'question': question, 'mode': mode, 'request_id': str(uuid4()),
                    'external_processing_confirmed': True,
                })
            st.session_state.pop('local_search', None)
        st.rerun()
    local_search = answer_preview(st.session_state.get('local_search'))
    if local_search is not None:
        st.subheader('Matching sources')
        st.info('No model was called. Open Search evidence to inspect matching passages, or use live Ask for a generated answer when available.')
        hits = local_search.get('hits', [])
        if not hits:
            st.info('No active evidence matched this question.')
        for hit in hits:
            st.caption('Source: ' + str(hit.get('filename', 'Document')) + ' · ' + page_label(hit.get('page')))
    value = st.session_state.get('answer')
    if value:
        error_description = describe_error(answer_preview(value)) if value.get('status') in {'llm_error', 'screening_error'} else None
        value = answer_view(value)
        st.subheader('Answer')
        st.write('Configuration:', value.get('mode'), '· Status:', value.get('status'))
        if isinstance(value.get('latency_ms'), (int, float)):
            st.caption(f"Elapsed: {value['latency_ms']/1000:.2f} seconds · Local units reserved: {value.get('reservation_units', 0)}")
        if value.get('status') in {'llm_error', 'screening_error'}:
            st.error(error_description)
            st.caption('This is the saved result of your previous submission; it is not retried on refresh.')
        else:
            st.text(value.get('answer') or value.get('error', ''))
        for ref in value.get('references', []):
            if ref.get('partial_text'):
                st.warning('This citation uses explicitly accepted partial extraction; unread content may affect the answer.')
            st.caption(f"Source: {ref.get('filename', 'Document')} · {page_label(ref.get('page'))}")
    st.divider()
    st.subheader('Compare A/B/C on one benign question')
    st.caption('One frozen retrieval result; up to 4 calls / 128000 units. Unreviewed interactive observations, not benchmark security metrics. No automatic retries.')
    capacity = (ready or {}).get('live', {})
    can_compare = (capacity.get('enabled', False) and capacity.get('remaining_calls', 0) >= 4
                   and capacity.get('remaining_reserved_tokens', 0) >= 128000)
    with st.form('benign-comparison'):
        comparison_question = st.text_area('Benign comparison question', max_chars=2000)
        compare_submit = st.form_submit_button('Compare once — up to 4 calls', disabled=not can_compare)
    if compare_submit and comparison_question.strip():
        with st.spinner('Running A, B, then C with the same initial evidence. Stops on error.'):
            st.session_state['comparison'] = api('POST', '/compare', json={
                'question': comparison_question, 'request_id': str(uuid4()),
                'external_processing_confirmed': True})
        st.rerun()
    comparison = st.session_state.get('comparison')
    if comparison:
        comparison = answer_preview(comparison)
        st.write('Comparison status:', comparison.get('status'))
        st.caption('Saved observations — semantic review pending; not rerun on refresh.')
        if comparison.get('error'):
            st.warning(comparison['error'])
        for column, label in zip(st.columns(3), 'ABC'):
            with column:
                st.write('Configuration ' + label)
                response = comparison.get('results', {}).get(label)
                if response is None:
                    st.info('Not executed.')
                else:
                    st.write('Status:', response.get('status'))
                    if response.get('status') in {'llm_error', 'screening_error'}:
                        st.error(describe_error(response))
                    else:
                        st.text(response.get('answer') or response.get('error', ''))
                    for reference in answer_view(response)['references']:
                        st.caption('Source: ' + str(reference.get('filename')) + ' · ' + page_label(reference.get('page')))
                    st.caption('Latency: ' + str(response.get('latency_ms')) + ' ms')
        st.download_button('Download answers and citations JSON', json.dumps(comparison_view(comparison), indent=2),
                           file_name='benign-comparison-unreviewed.json', mime='application/json')
if page == 'Metrics / evaluation':
    from frontend.metrics import render_metrics
    render_metrics(api, BASE)

if page == 'Saved experiments':
    runs = api('GET', '/results')
    names = (runs or {}).get('runs', [])
    if not names:
        st.info('No saved experiments. Run the evaluator CLI; no example metrics are presented as measurements.')
    else:
        name = st.selectbox('Experiment', names, format_func=answer_preview)
        value = answer_preview(api('GET', '/results/'+name))
        if value:
            st.json(value['experiment'], expanded=False)
            summary = value.get('summary') or {}
            coverage = summary.get('coverage', {})
            st.warning('Saved observations only. Human review and error coverage determine which metrics are eligible.')
            st.subheader('Assignment metrics')
            st.dataframe(metric_rows(summary), hide_index=True, use_container_width=True)
            st.caption('Rates show numerator/denominator. N/A is not zero. Screening flags and blocks are observed behavior; false-positive judgments require benign-case review. Latency includes saved failed routes. Different models/prompt versions must not be pooled.')
            st.write('Review coverage', coverage)
            st.json(summary, expanded=False)
            with st.expander('Download actual results and human-review records'):
                st.caption('These downloads are masked previews. Original records remain local for review using the documented CLI. Review templates contain blank judgments; downloading does not approve a result.')
                for artifact in ['records.csv','comparison.csv','review-template.json','review-packets.json','operational-summary.json']:
                    content = artifact_bytes(name, artifact)
                    if content is not None:
                        st.download_button('Download masked '+artifact, artifact_preview(content, filename=artifact),
                                           file_name=answer_preview(name)+'-masked-'+artifact, key=name+artifact)
            with st.expander('Metric charts — check denominators and review status'):
                for artifact in ['asr','exposed_asr','benign_task_success','benign_false_flags','benign_false_blocks','quality','latency']:
                    content = artifact_bytes(name, artifact+'.png')
                    if content is not None:
                        st.image(content, caption=artifact.replace('_',' '))
            cases = sorted({row['case_id'] for row in value['results']})
            for case_id in cases:
                grouped = {row['mode']:row for row in value['results'] if row['case_id']==case_id}
                with st.expander(case_id):
                    first = next(iter(grouped.values()))
                    st.text(first.get('case', {}).get('query', ''))
                    for column, mode in zip(st.columns(3), 'ABC'):
                        with column:
                            st.write('Configuration '+mode)
                            row = grouped.get(mode)
                            if row is None:
                                st.info('No saved execution for this configuration.')
                                continue
                            response = row['response']
                            st.write('Status:', response['status'])
                            if response['status'] in {'llm_error','screening_error'}:
                                st.error(describe_error(response))
                            else:
                                st.text(response.get('answer',''))
                            judgment = row.get('judgment', {})
                            st.caption('Human reviewed' if judgment.get('reviewer') else 'Human review pending / operational error ungraded')
                            if judgment.get('reviewer'):
                                st.json({k:judgment.get(k) for k in ['attack_success','task_success','quality','notes']}, expanded=False)
                            for ref in response.get('references', []):
                                st.text(ref['filename']+' · '+ref['section']+' · '+ref['id'])
                                with st.expander('Source excerpt — masked document text'):
                                    st.text(ref['text'])
                            st.json({'screening':response.get('screening'),
                                     'original_evidence':response.get('candidate_evidence',[]),
                                     'retained_evidence':response.get('supplied_evidence',[])}, expanded=False)

if page == 'Saved experiments':
    st.divider()
    st.subheader('Separate provider diagnostics')
    st.caption('Operational evidence only. A provider rejection is not an application-defense success.')
    diagnostics = api('GET', '/diagnostics') or {}
    for diagnostic_id in diagnostics.get('diagnostics', []):
        with st.expander(answer_preview(diagnostic_id)):
            st.json(answer_preview(api('GET', '/diagnostics/'+diagnostic_id)), expanded=False)
