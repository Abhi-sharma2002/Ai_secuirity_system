"""Read-only metric inspection. No provider request or evaluation run controls."""
import json

import httpx
import streamlit as st

from frontend.presentation import answer_preview, evaluation_metric_rows
from frontend.redaction import artifact_preview


def render_metrics(api, base):
    st.subheader('Evaluation metrics — v3')
    st.caption('Local CSV records only. Opening or refreshing this page makes no model calls.')
    if st.button('Refresh local metrics'):
        st.rerun()
    value = api('GET', '/evaluation-v3')
    if value is None:
        st.info('Check the local evaluation files, then regenerate reports with the commands below.')
    else:
        value = answer_preview(value)
        counts = value['counts']
        st.write('Recorded:', counts['recorded'], '/', counts['expected'], '· Missing:', counts['missing'],
                 '· Errors:', counts['errors'], '· Awaiting review:', counts['needs_review'],
                 '· Human quality scores:', counts['quality_reviewed'])
        if value['status'] == 'no_records':
            st.info('No live v3 evaluation records exist yet. N/A means unavailable; no defense winner can be inferred.')
        elif value['status'] == 'partial':
            st.warning('Partial comparison: inspect missing, error and review counts before comparing rates.')
        else:
            st.caption('All case/mode rows are recorded. Error exclusions and human-review coverage still affect interpretation.')
        st.dataframe(evaluation_metric_rows(value['summary'], value['definitions']), hide_index=True, height=500)
        coverage = [{k: row[k] for k in ('mode', 'n_recorded', 'n_expected', 'n_missing', 'n_adversarial',
                    'n_benign', 'n_errors', 'n_needs_review', 'n_quality', 'n_agreement', 'n_latency')}
                    for row in value['summary']]
        with st.expander('Counts, denominators and raw computed summary'):
            st.dataframe(coverage, hide_index=True)
            st.json(value['summary'], expanded=False)
        with st.expander('Metric definitions and interpretation', expanded=True):
            st.dataframe([{k: d[k] for k in ('metric', 'formula', 'better')} for d in value['definitions']], hide_index=True)
            for note in value['notes']:
                st.text(note)
        with st.expander('Evaluation configuration and dataset'):
            st.json({'configuration': value['configuration'], 'dataset': value['dataset'],
                     'recorded_origin': value['origin'], 'provider_execution_enabled': value['provider_execution_enabled']})

        def artifact(name):
            try:
                response = httpx.get(base + '/evaluation-v3/artifacts/' + name, timeout=15)
                return response.content if response.status_code == 200 else None
            except httpx.HTTPError:
                return None

        chart_labels = [('asr.png', 'Attack success — all versus exposed'),
                        ('benign_success.png', 'Benign task success'),
                        ('false_positive.png', 'C false-positive types'),
                        ('latency.png', 'Mean and p95 latency'),
                        ('asr_by_category.png', 'Attack success by category'),
                        ('tradeoff.png', 'Security versus usability trade-off')]
        with st.expander('All six PDF charts', expanded=True):
            if not value['charts_current']:
                st.warning('Saved charts are missing or stale. Regenerate the local report; stale charts are withheld.')
            else:
                for filename, label in chart_labels:
                    content = artifact(filename) if filename in value['artifacts'] else None
                    if content is None:
                        st.info(label + ': artifact unavailable; regenerate the local report.')
                    else:
                        st.image(content, caption=label)
                        st.download_button('Download ' + filename, content, file_name=filename, mime='image/png')
        with st.expander('Download saved tables, review forms and written explanations'):
            st.caption('Text downloads are masked preview copies; original evaluation files remain local. Regenerate written reports after updating records or human labels.')
            for filename in value['artifacts']:
                if filename.endswith('.png') or (filename == 'summary.csv' and not value['charts_current']):
                    continue
                content = artifact(filename)
                if content is not None:
                    st.download_button('Download masked ' + filename, artifact_preview(content, filename=filename),
                                       file_name='masked-' + filename)

        rows = value['records']
        st.subheader('Inspect recorded cases')
        if not rows:
            st.caption('Case answers, screening decisions and evidence will appear here after real records exist.')
        else:
            st.caption('Inspection uses masked copies. Consult the original local records for exact synthetic markers when making human judgments; masking never changes metric calculations.')
            mode = st.selectbox('Recorded configuration', ['All', 'A', 'B', 'C'])
            scope = st.selectbox('Record status', ['All', 'Errors', 'Needs human review', 'Eligible for metrics'])
            selected = [r for r in rows if (mode == 'All' or r['mode'] == mode)
                        and (scope == 'All' or (scope == 'Errors' and r['error'].strip())
                             or (scope == 'Needs human review' and not r['error'].strip() and r['needs_review'] == 'true')
                             or (scope == 'Eligible for metrics' and not r['error'].strip() and r['needs_review'] == 'false'))]
            if not selected:
                st.info('No recorded rows match these filters.')
            else:
                st.dataframe([{k: r[k] for k in ('case_id', 'mode', 'category', 'channel', 'attack_retrieved',
                              'attack_succeeded', 'task_passed', 'blocked', 'needs_review', 'citation_correct', 'error')}
                              for r in selected], hide_index=True)
                keys = [r['case_id'] + ' / ' + r['mode'] for r in selected]
                choice = st.selectbox('Inspect case / configuration', keys)
                row = selected[keys.index(choice)]
                with st.expander('Question, answer, citations and screening trace', expanded=True):
                    st.text('Question: ' + row['query'])
                    st.text('Expected behavior: ' + row['expected_behavior'])
                    st.text('Recorded answer: ' + row['answer'])
                    st.json(value.get('case_metadata', {}).get(row['case_id'], {}), expanded=False)
                    detail = {}
                    for key, item in row.items():
                        if key in {'sources', 'retrieved_chunk_ids', 'kept_chunk_ids', 'removed_chunk_ids', 'screen_reasons'}:
                            try:
                                item = json.loads(item)
                            except (ValueError, TypeError):
                                pass
                        detail[key] = item
                    st.json(answer_preview(detail), expanded=False)
                if st.checkbox('Inspect saved original retrieval for this case'):
                    evidence = api('GET', '/evaluation-v3/evidence/' + row['case_id'])
                    if evidence is not None:
                        st.json(answer_preview(evidence), expanded=False)
    st.caption('Local reporting commands — they do not enable provider evaluation:')
    st.code('.venv/bin/python backend/scripts/make_report.py\n'
            '.venv/bin/python backend/scripts/review_eval.py --prepare\n'
            '.venv/bin/python backend/scripts/write_report.py\n'
            '.venv/bin/python backend/scripts/write_report.py --check', language='bash')
