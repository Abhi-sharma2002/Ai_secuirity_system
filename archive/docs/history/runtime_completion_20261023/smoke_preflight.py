"""Read-only, secret-safe preparation for three development cases; never executes LLM calls."""
import argparse
import hashlib
import importlib.util
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from pydantic import ValidationError
from app.core.config import LiveSettings, settings
from app.evaluation import experiment as exp
from app.llm.client import Approval

CASE_IDS = ['development-01', 'development-02', 'development-07']
RUN_ID = 'dev-smoke-20261020-v1'


def local_status(config, workload):
    path=config.allowance_file
    result={'provider':'groq','credentials_present':bool(config.api_key),
        'model_configured':bool(config.model),'live_enabled':config.enabled,'free_only':config.free_only,
        'provider_sdk_installed':importlib.util.find_spec('langchain_groq') is not None,
        'allowance_path_configured':path is not None,'allowance_exists':bool(path and path.is_file()),
        'allowance_schema_valid':False,'allowance_model_matches':None,'allowance_not_expired':None,
        'allowance_free_confirmed':None,'allowance_capabilities_confirmed':None,
        'allowance_total_budget_sufficient':None,'allowance_remaining_budget_sufficient':None,
        'ledger_checked_read_only':False,'local_approval_checks_pass':False}
    if not result['allowance_exists']:return result
    try:
        if path.stat().st_size>10000:
            result['allowance_error']='file_exceeds_size_bound';return result
        approved=Approval.model_validate_json(path.read_text())
    except ValidationError as exc:
        result['allowance_error']='schema_invalid'
        # Do not serialize Pydantic errors: they contain original input/possible secrets.
        result['schema_issue_fields']=sorted({str(e['loc'][0]) for e in exc.errors()
            if e['loc'] and e['loc'][0] in Approval.model_fields})
        return result
    except Exception:
        result['allowance_error']='unreadable_or_invalid_json';return result
    result.update(allowance_schema_valid=True,
        allowance_model_matches=bool(config.model) and approved.approved_model==config.model,
        allowance_not_expired=approved.expires_at.tzinfo is not None and approved.expires_at>datetime.now(timezone.utc),
        allowance_free_confirmed=approved.confirmed_free_promotional,
        allowance_capabilities_confirmed=all((approved.chat_completions_supported,
            approved.structured_outputs_supported,approved.max_output_tokens_supported)),
        allowance_total_budget_sufficient=approved.max_calls>=workload['maximum_api_calls_without_retries'] and approved.max_reserved_tokens>=workload['conservative_reserved_tokens'])
    dbpath=settings.app_data_directory/'registry.sqlite3'
    try:
        if dbpath.exists():
            with sqlite3.connect(dbpath.as_uri()+'?mode=ro',uri=True) as db:
                used=[json.loads(row[0]) for row in db.execute('SELECT data FROM calls WHERE allowance_id=?',(approved.allowance_id,))]
                fingerprint=hashlib.sha256(approved.model_dump_json().encode()).hexdigest()
                stopped=db.execute('SELECT stopped FROM allowance WHERE id=?',(fingerprint,)).fetchone()
            quota_stopped=bool(stopped and stopped[0]) or any(row.get('error') in {'insufficient_quota','quota_or_rate_limit'} for row in used)
        else:used=[];quota_stopped=False
        result.update(ledger_checked_read_only=True,allowance_quota_stopped=quota_stopped,
            allowance_remaining_budget_sufficient=not quota_stopped and
                len(used)+workload['maximum_api_calls_without_retries']<=approved.max_calls and
                sum(row.get('reservation',0) for row in used)+workload['conservative_reserved_tokens']<=approved.max_reserved_tokens)
    except Exception:result['ledger_error']='cannot_verify_cumulative_usage'
    result['local_approval_checks_pass']=all(result[k] is True for k in (
        'allowance_schema_valid','allowance_model_matches','allowance_not_expired',
        'allowance_free_confirmed','allowance_capabilities_confirmed',
        'allowance_total_budget_sufficient','allowance_remaining_budget_sufficient'))
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True)
    args=p.parse_args()
    workload=exp.plan('development',1,case_ids=CASE_IDS)
    config=LiveSettings.from_env()
    status=local_status(config,workload)
    folder=exp.reg.ROOT/'experiments'/RUN_ID
    report={'provenance':{'author_role':'agent','human_approved':False,'live_calls':0},
        'run_id':RUN_ID,'result_directory':str(folder),'fresh_result_directory':not folder.exists(),
        'protocol':'paired','evidence_scope':'retrieved within each case fixture allowlist; not full corpus',
        'workload':workload,'status':status,'retrieval_settings':{'top_k':settings.top_k,
        'chunk_size':settings.chunk_size,'chunk_overlap':settings.chunk_overlap,'context_text_bytes':12000},
        'provider_readiness':'unconfirmed; local validation does not attest access or actual free entitlement'}
    with args.output.open('x') as out:json.dump(report,out,indent=2)
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
