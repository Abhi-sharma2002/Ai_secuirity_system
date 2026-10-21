"""Read-only preparation for one benign paired smoke. No execute path or live calls.
Reuse the existing planner and gate diagnostics; only the requested report is written.
"""
import argparse
import hashlib
import importlib.metadata
import json
from pathlib import Path
import sqlite3
from unittest.mock import patch

from app.core.config import LiveSettings, settings
from app.evaluation import experiment as exp
from app.evaluation.dataset import Manifest, Annotations
from app.ingestion import indexer, parsers
from app.llm import client as live
from app.rag import assistant
from scripts.smoke_preflight import local_status

CASE_ID = 'development-02'
RUN_ID = 'phase6-benign-20261021-v1'


def accounting(config):
    a = live.Approval.model_validate_json(config.allowance_file.read_text())
    path = settings.app_data_directory/'registry.sqlite3'
    rows = []
    if path.exists():
        with sqlite3.connect(path.as_uri()+'?mode=ro', uri=True) as db:
            rows = [json.loads(r[0]) for r in db.execute('SELECT data FROM calls WHERE allowance_id=?', (a.allowance_id,))]
    return {'reserved_call_records': len(rows), 'reserved_tokens_used': sum(r.get('reservation', 0) for r in rows),
            'remaining_calls': a.max_calls-len(rows),
            'remaining_reserved_tokens': a.max_reserved_tokens-sum(r.get('reservation', 0) for r in rows),
            'approval_fingerprint': hashlib.sha256(a.model_dump_json().encode()).hexdigest()}


def prepare():
    c = LiveSettings.from_env()
    if not c.free_only or c.enabled:
        raise ValueError('Offline preparation requires FREE_ONLY=true and LIVE_LLM_ENABLED=false')
    raw = (exp.DATASET/'manifest.json').read_bytes()
    data = Manifest.model_validate_json(raw).model_dump()
    annotations = Annotations.model_validate_json((exp.DATASET/'annotations.json').read_bytes())
    assert annotations.manifest_sha256 == hashlib.sha256(raw).hexdigest()
    case = next(x for x in data['cases'] if x['case_id']==CASE_ID)
    annotation = next(x for x in annotations.cases if x.case_id==CASE_ID)
    assert case['split']=='development' and not case['adversarial']
    assert annotation.kind=='benign' and annotation.benign_material=='ordinary' and not annotation.attack_locations
    # Previously validated frozen manifest supplies real case data. Reuse the
    # planner, without rerunning full-corpus parsing from completed phases.
    with patch.object(exp, 'load', return_value=data):
        workload = exp.plan('development', 1, case_id=CASE_ID)
    fixture = next(f for f in data['fixtures'] if f['fixture_id']==case['fixtures'][0])
    source = (exp.DATASET/fixture['path']).read_bytes()
    assert hashlib.sha256(source).hexdigest()==fixture['sha256']
    parsed = parsers._extract(source, Path(fixture['path']).suffix)
    assert parsed['status']=='parsed'
    for span in annotation.support:
        b = parsed['blocks'][span.block]
        assert b['text'][span.start:span.end]==span.quote
    snap = json.loads((exp.DATASET/'snapshot.json').read_text())
    assert snap['dataset_hash']==exp.digest(data) and snap['configuration']==indexer.index_configuration()
    assert snap['parser_version']==parsers.PARSER_VERSION
    assert (snap['chunk_size'],snap['chunk_overlap'])==(settings.chunk_size,settings.chunk_overlap)
    items = [snap['items'][key] for key in case['fixtures']]
    # A preparation may query existing indexes, but cannot silently build them.
    with patch.object(indexer, 'index_documents', side_effect=AssertionError('No indexing in preparation')):
        initial = exp.search(case['query'], items)
    assert initial['hits'] and all(h['version_id'] in {i['id'] for i in items} for h in initial['hits'])
    assert all(any(span.quote in h['text'] for h in initial['hits']) for span in annotation.support)
    status = local_status(c, workload)
    budget = accounting(c)
    folder = settings.app_data_directory/'experiments'/RUN_ID
    policy = next(p for p in annotations.policies if p.policy_id==annotation.policy_id)
    identity = {'provider': 'groq', 'model': c.model, 'api': 'chat_completions', 'temperature': 1.0,
                'max_output_tokens': 700, 'sdk_retries': 0, 'repair_attempts': 0,
                'request_timeout_seconds': c.request_timeout_seconds, 'top_k': settings.top_k,
                'context_text_bytes': 12000, 'chunk_size': settings.chunk_size, 'chunk_overlap': settings.chunk_overlap,
                'index_configuration': indexer.index_configuration(), 'prompt_hash': assistant.PROMPT_HASH,
                'manifest_sha256': hashlib.sha256(raw).hexdigest(), 'snapshot_hash': exp.digest(snap),
                'annotation_sha256': hashlib.sha256((exp.DATASET/'annotations.json').read_bytes()).hexdigest(),
                'scoring_spec_sha256': hashlib.sha256(exp.SCORING_SPEC.read_bytes()).hexdigest(),
                'package_versions': {name: importlib.metadata.version(name) for name in ('langchain-groq','groq','langchain-core')},
                'code_sha256': {str(p.relative_to(exp.DATASET.parents[1])): hashlib.sha256(p.read_bytes()).hexdigest()
                    for p in (Path(assistant.__file__), Path(live.__file__), Path(exp.__file__))}}
    return {'status': 'Phase 6 prepared; live execution pending', 'author_role':'agent', 'human_approved':False,
            'provider_calls':0, 'case_id':CASE_ID, 'question':case['query'], 'protocol':'paired', 'seed':5,
            'mode_order':['A','B','C'], 'repetitions':1, 'scope':'case fixture allowlist, not full corpus',
            'support': [s.model_dump() for s in annotation.support], 'expected_behavior':policy.behavior,
            'expected_facts':policy.facts, 'semantic_review_required':True,
            'initial_retrieved_evidence':initial, 'c_screening':None, 'c_retained_evidence':None,
            'answers':None, 'actual_usage':None, 'actual_latency':None,
            'workload':workload, 'identity':identity, 'readiness':status, 'local_budget':budget,
            'run_id':RUN_ID, 'output_directory':str(folder), 'fresh_run_directory':not folder.exists(),
            'blockers':[reason for reason, ok in (
                ('Actual free entitlement remains unconfirmed', status.get('allowance_free_confirmed')),
                ('Local allowance cannot fund the unchanged full reservation ceiling', status.get('allowance_remaining_budget_sufficient')),
                ('Selected run directory already exists; do not resume/retry this smoke', not folder.exists())) if not ok],
            'execution_authorized':False}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    if args.output.exists():
        p.error('Choose a new output path; existing preparation is preserved')
    with patch('socket.socket.connect', side_effect=AssertionError('Offline preparation: network forbidden')), \
         patch('socket.create_connection', side_effect=AssertionError('Offline preparation: network forbidden')), \
         patch.object(live, 'call', side_effect=AssertionError('No provider calls in preparation')), \
         patch.object(live, 'reserve', side_effect=AssertionError('No reservations in preparation')):
        result = prepare()
    with args.output.open('x') as out:
        json.dump(result, out, indent=2)
    print(json.dumps({'status':result['status'], 'case_id':CASE_ID, 'provider_calls':0,
                      'output':str(args.output), 'blockers':result['blockers']}))


if __name__=='__main__':
    main()
