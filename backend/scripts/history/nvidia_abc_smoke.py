"""Exclusive NVIDIA development-02 paired smoke: <=4 attempts, 128000 new units."""
from copy import deepcopy
from datetime import datetime,timedelta,timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
from unittest.mock import patch
import time
from app.storage import registry as reg
from app.core.config import LiveSettings,settings
from app.llm import client as live
from app.rag import assistant
from app.evaluation import experiment as exp
from scripts.history import phase6_auth_attempt as bound
from scripts.phase6_smoke import RequestPacer
from scripts.history.groq_restore_attempt import public_accounting

RUN_ID='nvidia-development-02-ABC-20261022-v1'
BASELINE='nvidia-development-02-A-20261022-v1'


def frozen_inputs():
    baseline=json.loads((reg.ROOT/'experiments'/BASELINE/'integration-diagnostics.json').read_text())
    prepared=json.loads(bound.PREPARED.read_text());identity=prepared['identity']
    raw=(exp.DATASET/'manifest.json').read_bytes()
    snapshot=json.loads((exp.DATASET/'snapshot.json').read_text())
    if (hashlib.sha256(raw).hexdigest()!=identity['manifest_sha256'] or
        exp.digest(snapshot)!=identity['snapshot_hash'] or assistant.PROMPT_HASH!=identity['prompt_hash'] or
        (settings.top_k,settings.chunk_size,settings.chunk_overlap)!=(5,1000,150)):
        raise live.LiveBlocked('Frozen data/prompt/retrieval identity changed')
    data=json.loads(raw)
    case=next(case for case in data['cases'] if case['case_id']=='development-02')
    initial=baseline['initial_retrieved_evidence']
    if initial!=prepared['initial_retrieved_evidence'] or case['query']!=prepared['question']:
        raise live.LiveBlocked('Baseline initial context/question differs')
    return data,snapshot,initial


def run_bounded(folder,data,snapshot,initial,c,diagnostic):
    original_call,original_reserve=live.call,live.reserve
    pacer=RequestPacer();reservations={}
    def save():bound.write(folder/'integration-diagnostics.json',diagnostic)
    save()
    case=next(case for case in data['cases'] if case['case_id']=='development-02')
    expected_items=[snapshot['items'][fixture] for fixture in case['fixtures']]
    def frozen_search(question,items):
        if question!=case['query'] or items!=expected_items:
            raise live.LiveBlocked('Question or fixture scope changed')
        return deepcopy(initial)  # reuse genuinely retrieved frozen baseline evidence
    def reserve(calls,tokens,metadata=None):
        mode=(metadata or {}).get('mode')
        if ((calls,tokens)!=(2,64000) if mode=='C' else (calls,tokens)!=(1,32000)) or mode not in 'ABC':
            raise live.LiveBlocked('Unexpected mode reservation')
        if diagnostic['reserved_calls']+calls>4 or diagnostic['reserved_tokens']+tokens>128000:
            raise live.LiveBlocked('Smoke reservation ceiling reached')
        ids=original_reserve(calls,tokens,metadata)
        reservations.update({rid:mode for rid in ids})
        diagnostic['reserved_calls']+=calls;diagnostic['reserved_tokens']+=tokens;save()
        return ids
    def call(messages,schema,stage,reservation):
        n=len(diagnostic['attempts']);mode=reservations.get(reservation)
        order=[('A','generation'),('B','generation'),('C','screening'),('C','generation')]
        if n>=4 or (mode,stage)!=order[n]:
            raise live.LiveBlocked('Unexpected provider attempt/order; no request')
        waited=pacer.wait()
        row={'mode':mode,'stage':stage,'reservation':reservation,'response':None,'usage':None,
             'provider_request_id':None,'schema_valid':None,'outcome':'interrupted_or_unknown',
             'pacing_wait_seconds':waited,'boundary_started_monotonic':pacer.clock()}
        diagnostic['attempts'].append(row);save();start=time.perf_counter()
        try:
            raw,record=original_call(messages,schema,stage,reservation)
            row.update(outcome='returned',response=json.loads(raw),client_record=record,
                       usage=record.get('usage'),provider_request_id=record.get('provider_request_id'))
            contract=assistant.Screening if stage=='screening' else assistant.Answer
            try:contract.model_validate_json(raw);row['schema_valid']=True
            except Exception:row['schema_valid']=False
            return raw,record
        except live.ModelFailure as exc:
            row.update(outcome=exc.category,client_record=exc.record,usage=exc.record.get('usage'),
                       provider_request_id=exc.record.get('provider_request_id'));raise
        except live.LiveBlocked:
            row['outcome']='blocked_before_provider';raise
        finally:
            pacer.finished();row['boundary_latency_ms']=(time.perf_counter()-start)*1000;save()
    started=time.perf_counter()
    try:
        with patch.object(live,'reserve',side_effect=reserve),patch.object(live,'call',side_effect=call), \
             patch.object(exp,'load',return_value=data),patch.object(exp,'prepare',return_value=snapshot), \
             patch.object(exp,'search',side_effect=frozen_search):
            exp.run(RUN_ID,'development','paired',1,5,True,case_id='development-02')
        diagnostic['outcome']='runner_completed_review_pending'
    except BaseException:
        diagnostic['outcome']='stopped_on_operational_error_or_interrupt_no_retry';raise
    finally:
        diagnostic['elapsed_seconds_including_pacing']=(time.perf_counter()-started)
        diagnostic['accounting_after']=public_accounting(c)
        diagnostic['case_results']={mode:json.loads(path.read_text())['response'] if path.exists() else None
            for mode in 'ABC' for path in [folder/f'case-development-02-{mode}-0.json']}
        save()


def execute():
    c=LiveSettings.from_env()
    if c.enabled or not c.free_only or c.provider!='nvidia_nim':raise live.LiveBlocked('Initial flags/provider mismatch')
    if (c.model!='nvidia/nemotron-3.5-super-vl-120b-a12b' or c.base_url!='https://integrate.api.nvidia.com/v1' or
        c.request_timeout_seconds!=30 or c.auth_mode!='bearer' or not c.api_key):raise live.LiveBlocked('NVIDIA request identity mismatch')
    bound.check_stops(c)
    approved=live.Approval.model_validate_json(c.allowance_file.read_text())
    if not approved.confirmed_free_promotional or not approved.eligibility_evidence:
        raise live.LiveBlocked('Missing current free eligibility evidence')
    if approved.provider!=c.provider or approved.approved_model!=c.model or approved.entitlement_expiry!='unknown':
        raise live.LiveBlocked('Existing approval differs from accepted provider/model/expiry policy')
    data,snapshot,initial=frozen_inputs()
    folder=reg.ROOT/'experiments'/RUN_ID;folder.mkdir(parents=True,exist_ok=False)
    before=public_accounting(c);now=datetime.now(timezone.utc)
    raw=approved.model_dump();raw.update(max_calls=before['reserved_call_records']+4,
        max_reserved_tokens=before['reserved_tokens_used']+128000,activated_at=now,
        eligibility_checked_at=now,expires_at=now+timedelta(hours=1),
        eligibility_evidence=approved.eligibility_evidence+' Accepted current-eligibility attestation reviewed for the authorized paired smoke. No fresh provider quota observation; local budget is not remaining provider quota.',
        confirmation_note='Operator authorizes one paired development-02 A/B/C repetition, seed5, <=4 provider attempts and128000 additional units beyond cumulative consumption. Same identity/history; no retries, repairs, reruns, fallbacks or probes. Unknown provider entitlement; one-hour local approval only; finish live disabled.')
    active=live.Approval.model_validate(raw)
    assert active.allowance_id==approved.allowance_id
    root_before=Path('.env').read_bytes()
    with reg.connect() as db:
        prior_calls={r['id']:tuple(r) for r in db.execute('SELECT * FROM calls')}
        prior_allowances={r['id']:tuple(r) for r in db.execute('SELECT * FROM allowance')}
    diagnostic={'run_id':RUN_ID,'baseline_run_id':BASELINE,'provider':c.provider,'model':c.model,
        'base_url':c.base_url,'question':next(case['query'] for case in data['cases'] if case['case_id']=='development-02'),
        'protocol':'paired','seed':5,'mode_order':['A','B','C'],'initial_retrieved_evidence':initial,
        'retrieval':'reused frozen genuine baseline retrieval; same fixture scope, top_k5, chunks1000/150, context12000 bytes',
        'settings':{'output_cap':700,'timeout_seconds':30,'temperature':1.0,'retries':0},
        'pacing':{'minimum_gap_seconds':65,'mechanism':'existing RequestPacer; wait65s after previous boundary completion'},
        'approval_updated_at':now.isoformat(),'local_expires_at':active.expires_at.isoformat(),
        'provider_entitlement_expiry':'unknown','accounting_before':before,'allowance_max_calls_after':active.max_calls,
        'allowance_max_units_after':active.max_reserved_tokens,'reserved_calls':0,'reserved_tokens':0,
        'attempts':[],'outcome':'authorized','full_benchmark_complete':False,'integration_passed':None}
    def save():bound.write(folder/'integration-diagnostics.json',diagnostic)
    save()
    pending=c.allowance_file.with_suffix('.smoke-tmp');fd=os.open(pending,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd,'w') as out:out.write(active.model_dump_json(indent=2))
    os.replace(pending,c.allowance_file)
    try:
        with patch.dict(os.environ,{'LIVE_LLM_ENABLED':'true','FREE_ONLY':'true'}):
            live.approval()
            run_bounded(folder,data,snapshot,initial,c,diagnostic)
    finally:
        diagnostic['root_env_unchanged']=Path('.env').read_bytes()==root_before
        diagnostic['final_process_live_disabled']=not LiveSettings.from_env().enabled
        with reg.connect() as db:
            after_calls={r['id']:tuple(r) for r in db.execute('SELECT * FROM calls')}
            after_allowances={r['id']:tuple(r) for r in db.execute('SELECT * FROM allowance')}
        diagnostic['prior_calls_unchanged']=all(after_calls.get(k)==v for k,v in prior_calls.items())
        diagnostic['prior_allowance_rows_and_stops_unchanged']=all(after_allowances.get(k)==v for k,v in prior_allowances.items())
        save()
    print(json.dumps({'run_id':RUN_ID,'outcome':diagnostic['outcome'],'attempts':len(diagnostic['attempts']),
        'accounting_after':diagnostic['accounting_after']}))


def main():
    import argparse
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--execute',action='store_true');args=p.parse_args()
    if not args.execute:p.error('--execute required')
    with (reg.ROOT/'backend.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);execute()


if __name__=='__main__':
    try:main()
    except Exception as exc:
        print(json.dumps({'outcome':'stopped_no_retry','exception_type':type(exc).__name__}));raise SystemExit(1)
