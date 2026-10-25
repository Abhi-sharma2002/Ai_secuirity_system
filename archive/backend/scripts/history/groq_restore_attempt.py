"""One authorized current-path A request, using the backend's inherited environment."""
import fcntl
import hashlib
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from app.storage import registry as reg
from app.core.config import LiveSettings
from app.llm import client as live
from app.rag import assistant
from app.evaluation import experiment as exp
from scripts.history import phase6_auth_attempt as base
from scripts.prepare_phase6 import accounting
from scripts.smoke_preflight import local_status

RUN_ID='groq-restore-development-02-A-20261022-v1'


def public_accounting(c):
    return {k:v for k,v in accounting(c).items() if k!='approval_fingerprint'}


def execute():
    c=LiveSettings.from_env()
    if c.enabled or not c.free_only:
        raise live.LiveBlocked('Initial process must be live disabled and free only')
    if c.model!='openai/gpt-oss-20b' or c.request_timeout_seconds!=30:
        raise live.LiveBlocked('Model or timeout changed')
    base.check_stops(c)
    prepared=json.loads(base.PREPARED.read_text())
    identity=prepared['identity']
    if (assistant.PROMPT_HASH!=identity['prompt_hash'] or
        hashlib.sha256((exp.DATASET/'manifest.json').read_bytes()).hexdigest()!=identity['manifest_sha256'] or
        exp.digest(json.loads((exp.DATASET/'snapshot.json').read_text()))!=identity['snapshot_hash']):
        raise live.LiveBlocked('Frozen evidence identity changed')
    status=local_status(c,base.WORKLOAD)
    fields=('credentials_present','provider_sdk_installed','allowance_schema_valid','allowance_model_matches',
            'allowance_free_confirmed','allowance_capabilities_confirmed','allowance_remaining_budget_sufficient')
    if not all(status.get(k) is True for k in fields):
        raise live.LiveBlocked('One-request prerequisite failed')
    folder=reg.ROOT/'experiments'/RUN_ID
    folder.mkdir(parents=True,exist_ok=False)
    root_before=Path('.env').read_bytes()  # compared in memory only; never persisted/hashed
    raw=json.loads(c.allowance_file.read_text())
    old_approval=dict(raw)
    now=datetime.now(timezone.utc)
    refreshed=live.Approval.model_validate(raw).expires_at<=now
    before=public_accounting(c)
    diagnostic={'run_id':RUN_ID,'linked_previous_runs':[base.ORIGINAL,base.RUN_ID],
        'authorized_at':now.isoformat(),'authorization':'One A/development-02 current-path provider request; expiry-only refresh; existing budgets; no retries/repairs/fallback/probes.',
        'configuration':'A','case_id':'development-02','seed':5,'model':c.model,'timeout_seconds':30,
        'max_output_tokens':700,'initial_retrieved_evidence':prepared['initial_retrieved_evidence'],
        'runtime_configuration':live.diagnostics.provenance(c),'accounting_before':before,
        'previous_expiry':raw['expires_at'],'expiry_refreshed':refreshed,
        'reserved_calls':0,'attempts':[],'outcome':'authorized','full_ABC_gate_complete':False,
        'provider_quota':'unknown; local expiry refresh does not establish quota'}
    def save():base.write(folder/'integration-diagnostics.json',diagnostic)
    save()
    if refreshed:
        raw['expires_at']=(now+timedelta(hours=1)).isoformat()
        live.Approval.model_validate(raw)
        assert {k:v for k,v in raw.items() if k!='expires_at'}=={k:v for k,v in old_approval.items() if k!='expires_at'}
        temporary=c.allowance_file.with_suffix('.restore-tmp')
        fd=os.open(temporary,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
        with os.fdopen(fd,'w') as out:json.dump(raw,out,indent=2)
        os.replace(temporary,c.allowance_file)
    diagnostic['expires_at']=raw['expires_at'];save()
    result=None
    try:
        if not local_status(c,base.WORKLOAD)['local_approval_checks_pass']:
            raise live.LiveBlocked('Updated approval not ready')
        with patch.dict(os.environ,{'LIVE_LLM_ENABLED':'true','FREE_ONLY':'true'}),patch.object(base,'RUN_ID',RUN_ID):
            result=base.bounded_response(prepared,diagnostic,save)
        base.write(folder/'case-development-02-A-0.json',result)
        diagnostic['outcome']=result['status']
        if result['status']=='answered':
            # Review the actual answer separately; no automatic grading.
            diagnostic['semantic_review']='pending review of actual answer and source text'
    finally:
        diagnostic['accounting_after']=public_accounting(c)
        diagnostic['root_env_unchanged']=Path('.env').read_bytes()==root_before
        diagnostic['final_process_live_disabled']=not LiveSettings.from_env().enabled
        save()
    print(json.dumps({'run_id':RUN_ID,'outcome':diagnostic['outcome'],
        'attempt_count':len(diagnostic['attempts']),'accounting_after':diagnostic['accounting_after'],
        'expires_at':diagnostic['expires_at']}))
    return 0 if result and result['status']=='answered' else 1


def main():
    import argparse
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--execute',action='store_true')
    args=p.parse_args()
    if not args.execute:p.error('Explicit --execute required')
    with (reg.ROOT/'backend.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        return execute()


if __name__=='__main__':
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(json.dumps({'outcome':'stopped_no_retry','exception_type':type(exc).__name__}))
        raise SystemExit(2)
