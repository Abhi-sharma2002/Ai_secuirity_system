"""Single-use A-only diagnostic; no retries, full-smoke invocation or config edits."""
import argparse
import fcntl
import hashlib
import json
import os
import sqlite3
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from app.core.config import LiveSettings, settings
from app.storage import registry as reg
from app.llm import client as live
from app.rag import assistant
from app.evaluation import experiment as exp
from scripts.prepare_phase6 import accounting
from scripts.smoke_preflight import local_status
from scripts.phase6_smoke import RequestPacer

RUN_ID = 'phase6-auth-A-20261022-v1'
ORIGINAL = 'phase6-benign-20261021-v1'
PREPARED = Path('docs/evidence/phase6-authorized-readiness-v1.json')
AUDIT = Path('docs/evidence/phase6-auth-A-authorization-v1.json')
WORKLOAD = {'maximum_api_calls_without_retries': 1, 'conservative_reserved_tokens': 32000}


def write(path, value):
    path.write_text(json.dumps(value, indent=2))


def check_stops(c):
    a = live.Approval.model_validate_json(c.allowance_file.read_text())
    with sqlite3.connect((settings.app_data_directory/'registry.sqlite3').as_uri()+'?mode=ro', uri=True) as db:
        rows = [json.loads(r[0]) for r in db.execute('SELECT data FROM calls WHERE allowance_id=?', (a.allowance_id,))]
        fingerprints = {r.get('approval_fingerprint') for r in rows}
        fingerprints.add(hashlib.sha256(a.model_dump_json().encode()).hexdigest())
        if any(stopped and identity in fingerprints for identity, stopped in db.execute('SELECT id,stopped FROM allowance')):
            raise live.LiveBlocked('Existing selected-allowance stop flag')
        if any(r.get('error') in {'insufficient_quota','quota_or_rate_limit'} for r in rows):
            raise live.LiveBlocked('Existing selected-allowance quota failure')


def validate_identity(c, prepared):
    identity = prepared['identity']
    assert c.model == identity['model'] == 'openai/gpt-oss-20b'
    assert c.request_timeout_seconds == identity['request_timeout_seconds'] == 30
    assert identity['max_output_tokens'] == 700 and prepared['seed'] == 5
    assert prepared['case_id'] == 'development-02'
    assert assistant.PROMPT_HASH == identity['prompt_hash']
    for name, expected in identity['code_sha256'].items():
        assert hashlib.sha256((exp.DATASET.parents[1]/name).read_bytes()).hexdigest() == expected
    assert prepared['initial_retrieved_evidence']['hits']
    assert hashlib.sha256((exp.DATASET/'manifest.json').read_bytes()).hexdigest() == identity['manifest_sha256']
    assert exp.digest(json.loads((exp.DATASET/'snapshot.json').read_text())) == identity['snapshot_hash']


def authorize():
    c = LiveSettings.from_env()
    assert not c.enabled and c.free_only
    assert not AUDIT.exists() and not (reg.ROOT/'experiments'/RUN_ID).exists()
    validate_identity(c, json.loads(PREPARED.read_text()))
    check_stops(c)
    status = local_status(c, WORKLOAD)
    assert all(v is True for k,v in status.items() if k in (
        'allowance_schema_valid','allowance_model_matches','allowance_free_confirmed',
        'allowance_capabilities_confirmed','allowance_remaining_budget_sufficient'))
    assert status['credentials_present'] and status['provider_sdk_installed']
    before = accounting(c)
    raw = json.loads(c.allowance_file.read_text())
    now = datetime.now(timezone.utc)
    previous = raw['expires_at']
    refreshed = live.Approval.model_validate(raw).expires_at <= now
    if refreshed:
        raw['expires_at'] = (now+timedelta(hours=1)).isoformat()
        live.Approval.model_validate(raw)
        temporary = c.allowance_file.with_suffix('.phase6-tmp')
        fd = os.open(temporary, os.O_WRONLY|os.O_CREAT|os.O_EXCL, 0o600)
        with os.fdopen(fd, 'w') as out:
            json.dump(raw, out, indent=2)
        os.replace(temporary, c.allowance_file)
    audit = {'run_id':RUN_ID,'linked_original_run':ORIGINAL,'authorized_at':now.isoformat(),
        'authorization':'User authorizes exactly one A-only development-02 diagnostic, seed 5, 32000 new units, output 700, timeout 30s, zero retries/repairs/fallbacks; expiry-only renewal if expired.',
        'expiry_refreshed':refreshed,'previous_expiry':previous,'expires_at':raw['expires_at'],
        'provider_quota_freshness':'unknown; local renewal does not prove provider quota',
        'accounting_before':before,'accounting_after_expiry_update':accounting(c),
        'root_env_sha256':hashlib.sha256(Path('.env').read_bytes()).hexdigest(),
        'status':local_status(c,WORKLOAD)}
    assert audit['status']['local_approval_checks_pass']
    with AUDIT.open('x') as out: json.dump(audit,out,indent=2)
    print(json.dumps({'authorization_record':str(AUDIT),'expiry_refreshed':refreshed,'ready':True}))


def bounded_response(prepared, diagnostic, save):
    original_reserve, original_call = live.reserve, live.call
    pacer = RequestPacer()
    def reserve(calls,tokens,metadata=None):
        if diagnostic['reserved_calls'] or (calls,tokens)!=(1,32000):
            raise live.LiveBlocked('A-only single reservation ceiling')
        # Count before entering the gate, including blocked or interrupted entries.
        diagnostic['reserved_calls']=1
        diagnostic['reservation_requested_units']=32000
        save()
        ids=original_reserve(calls,tokens,metadata)
        diagnostic['reservation_ids']=ids
        save()
        return ids
    def call(messages,schema,stage,reservation):
        if diagnostic['attempts'] or stage!='generation' or reservation not in diagnostic.get('reservation_ids',[]):
            raise live.LiveBlocked('A-only single boundary ceiling')
        row={'stage':stage,'reservation':reservation,'response':None,'usage':None,
             'provider_request_id':None,'outcome':'interrupted_or_unknown',
             'pacing_wait_seconds':pacer.wait()}
        diagnostic['attempts'].append(row); save()
        start=time.perf_counter()
        try:
            raw, record=original_call(messages,schema,stage,reservation)
            row.update(outcome='returned',response=json.loads(raw),client_record=record,
                       usage=record.get('usage'),provider_request_id=record.get('provider_request_id'))
            return raw,record
        except live.ModelFailure as exc:
            row.update(outcome=exc.category,client_record=exc.record,usage=exc.record.get('usage'),
                       provider_request_id=exc.record.get('provider_request_id'))
            raise
        except live.LiveBlocked:
            row['outcome']='blocked_before_provider'; raise
        finally:
            pacer.finished(); row['latency_ms']=(time.perf_counter()-start)*1000;save()
    with patch.object(live,'reserve',side_effect=reserve),patch.object(live,'call',side_effect=call):
        return assistant.respond(prepared['question'],'A',initial=prepared['initial_retrieved_evidence'],
            run_context={'run_id':RUN_ID,'case_id':'development-02','seed':5,'linked_original_run':ORIGINAL,'diagnostic':True})


def execute():
    c=LiveSettings.from_env()
    assert c.enabled and c.free_only
    prepared=json.loads(PREPARED.read_text()); audit=json.loads(AUDIT.read_text())
    validate_identity(c,prepared);check_stops(c)
    assert accounting(c)==audit['accounting_after_expiry_update']
    assert local_status(c,WORKLOAD)['local_approval_checks_pass']
    assert hashlib.sha256(Path('.env').read_bytes()).hexdigest()==audit['root_env_sha256']
    folder=reg.ROOT/'experiments'/RUN_ID
    folder.mkdir(parents=True,exist_ok=False)
    diagnostic={'run_id':RUN_ID,'linked_original_run':ORIGINAL,'original_failure_record':
        str(reg.ROOT/'experiments'/ORIGINAL/'case-development-02-A-0.json'),
        'configuration':'A','case_id':'development-02','seed':5,'identity':prepared['identity'],
        'initial_retrieved_evidence':prepared['initial_retrieved_evidence'],
        'accounting_before':accounting(c),'accounting_after':None,'reserved_calls':0,'attempts':[],
        'pacing':{'minimum_request_start_gap_seconds':65,'mechanism':'existing RequestPacer'},
        'full_ABC_gate_complete':False,'outcome':'started'}
    def save(): write(folder/'integration-diagnostics.json',diagnostic)
    save()
    try:
        result=bounded_response(prepared,diagnostic,save)
        write(folder/'case-development-02-A-0.json',result)
        diagnostic['outcome']=result['status']
    finally:
        diagnostic['accounting_after']=accounting(c)
        diagnostic['root_env_unchanged']=hashlib.sha256(Path('.env').read_bytes()).hexdigest()==audit['root_env_sha256']
        save()
    print(json.dumps({'run_id':RUN_ID,'outcome':diagnostic['outcome'],'boundary_entries':len(diagnostic['attempts']),
        'accounting_after':diagnostic['accounting_after']}))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--authorize',action='store_true');p.add_argument('--execute',action='store_true')
    args=p.parse_args()
    assert args.authorize != args.execute
    with (reg.ROOT/'backend.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        (authorize if args.authorize else execute)()

if __name__=='__main__': main()
