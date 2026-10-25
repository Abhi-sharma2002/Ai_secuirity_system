"""Exclusive one-shot NVIDIA A/development-02 run under the amended gate."""
import fcntl
import hashlib
import json
import os
from datetime import datetime,timedelta,timezone
from pathlib import Path
from unittest.mock import patch
from app.storage import registry as reg
from app.core.config import LiveSettings
from app.llm import client as live
from app.rag import assistant
from app.evaluation import experiment as exp
from scripts.history import phase6_auth_attempt as bound
from scripts.history.groq_restore_attempt import public_accounting

RUN_ID='nvidia-development-02-A-20261022-v1'


def execute():
    c=LiveSettings.from_env()
    if c.enabled or not c.free_only or c.provider!='nvidia_nim':
        raise live.LiveBlocked('NVIDIA process must start live disabled and free only')
    if (c.base_url!='https://integrate.api.nvidia.com/v1' or c.auth_mode!='bearer' or
        c.model!='nvidia/nemotron-3.5-super-vl-120b-a12b' or c.request_timeout_seconds!=30 or not c.api_key):
        raise live.LiveBlocked('Configured NVIDIA request identity mismatch')
    bound.check_stops(c)
    a=live.Approval.model_validate_json(c.allowance_file.read_text())
    if not a.confirmed_free_promotional:
        raise live.LiveBlocked('Missing current free/promotional eligibility confirmation')
    if a.provider!=c.provider or a.approved_model!=c.model or (a.max_calls,a.max_reserved_tokens)!=(1,32000):
        raise live.LiveBlocked('Prepared NVIDIA allowance differs from one-call scope')
    if public_accounting(c)['remaining_calls']!=1 or public_accounting(c)['remaining_reserved_tokens']!=32000:
        raise live.LiveBlocked('One unused reservation required; no rerun')
    prepared=json.loads(bound.PREPARED.read_text());identity=prepared['identity']
    if (assistant.PROMPT_HASH!=identity['prompt_hash'] or
        hashlib.sha256((exp.DATASET/'manifest.json').read_bytes()).hexdigest()!=identity['manifest_sha256'] or
        exp.digest(json.loads((exp.DATASET/'snapshot.json').read_text()))!=identity['snapshot_hash']):
        raise live.LiveBlocked('Frozen input identity changed')
    folder=reg.ROOT/'experiments'/RUN_ID;folder.mkdir(parents=True,exist_ok=False)
    now=datetime.now(timezone.utc)
    updated=a.model_dump()
    updated.update(entitlement_expiry='unknown',activated_at=now,expires_at=now+timedelta(hours=1),
        eligibility_checked_at=now,
        eligibility_evidence='Operator explicitly confirmed current free/trial eligibility, exact-model access and enough remaining quota for one baseline request including other traffic. Operator reports no entitlement expiry shown. Accepted attestation reviewed at activation; no fresh dashboard or provider-quota observation is claimed.',
        confirmation_note='User authorizes one NVIDIA A/development-02 attempt under the 22 October 2026 unknown-expiry amendment. Provider entitlement expiry unknown, not unlimited; API key expiry unused. Local approval exactly one hour. Existing cap1/32000, output700, timeout30s, retries0; finish live disabled.')
    active=live.Approval.model_validate(updated)
    assert active.allowance_id==a.allowance_id and active.max_calls==a.max_calls and active.max_reserved_tokens==a.max_reserved_tokens
    root_before=Path('.env').read_bytes()
    d={'run_id':RUN_ID,'configuration':'A','case_id':'development-02','seed':5,'provider':c.provider,
       'model':c.model,'base_url':c.base_url,'output_cap':700,'timeout_seconds':30,'retries':0,
       'provider_entitlement_expiry':'unknown','activated_at':now.isoformat(),'local_expires_at':active.expires_at.isoformat(),
       'eligibility_evidence':active.eligibility_evidence,'eligibility_checked_at':now.isoformat(),
       'accounting_before':public_accounting(c),'initial_retrieved_evidence':prepared['initial_retrieved_evidence'],
       'reserved_calls':0,'attempts':[],'outcome':'activated','full_ABC_gate_complete':False}
    def save():bound.write(folder/'integration-diagnostics.json',d)
    save()
    temporary=c.allowance_file.with_suffix('.activation-tmp')
    fd=os.open(temporary,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd,'w') as out:out.write(active.model_dump_json(indent=2))
    os.replace(temporary,c.allowance_file)
    try:
        with patch.dict(os.environ,{'LIVE_LLM_ENABLED':'true','FREE_ONLY':'true'}),patch.object(bound,'RUN_ID',RUN_ID):
            live.approval()  # The actual gate, never mocked.
            result=bound.bounded_response(prepared,d,save)
        bound.write(folder/'case-development-02-A-0.json',result)
        d['outcome']=result['status']
        d['semantic_review']='pending' if result['status']=='answered' else 'No valid answer available for review'
    finally:
        d['accounting_after']=public_accounting(c)
        d['root_env_unchanged']=Path('.env').read_bytes()==root_before
        d['final_process_live_disabled']=not LiveSettings.from_env().enabled
        save()
    print(json.dumps({'run_id':RUN_ID,'outcome':d['outcome'],'attempt_count':len(d['attempts']),
       'accounting_after':d['accounting_after'],'local_expires_at':d['local_expires_at']}))
    return 0 if result['status']=='answered' else 1


def main():
    import argparse
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--execute',action='store_true');args=p.parse_args()
    if not args.execute:p.error('--execute required')
    with (reg.ROOT/'backend.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        return execute()


if __name__=='__main__':
    try:raise SystemExit(main())
    except Exception as exc:
        print(json.dumps({'outcome':'blocked_or_interrupted_no_retry','exception_type':type(exc).__name__}))
        raise SystemExit(2)
