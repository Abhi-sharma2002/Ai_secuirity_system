"""Single authorized trial-credit diagnostic, using existing gate and Bound.

No automatic action on import. Historical evaluation stop remains immutable.
"""
from pathlib import Path
from datetime import datetime,timedelta,timezone
from copy import deepcopy
import json,hashlib,os,fcntl
from unittest.mock import patch
from app.core.config import LiveSettings
from app.storage import registry as reg
from app.llm import client as live
from app.rag import assistant
from app.evaluation import experiment as exp
from scripts.azure_live_integration import Bound

ROOT=Path(__file__).resolve().parents[2]


def main():
    os.environ['LIVE_LLM_ENABLED']='false'
    config=LiveSettings.from_env()
    draft=json.loads((ROOT/'.private/azure_development07_diagnostic_receipt.DRAFT.json').read_text())
    parent_path=ROOT/'.private/azure_development_allowance_v1.json'
    parent_bytes=parent_path.read_bytes();parent=live.Approval.model_validate_json(parent_bytes)
    source=reg.ROOT/'experiments'/draft['parent']['run_id']
    failed=json.loads((source/'case-development-07-A-0.json').read_text())
    frozen_path=Path(draft['frozen_input']['retrieval_path'])
    if (hashlib.sha256(frozen_path.read_bytes()).hexdigest()!=draft['frozen_input']['retrieval_sha256']
            or exp.review_binding(failed)!=draft['frozen_input']['response_record_binding']
            or failed['response']['calls'][0]['call_id']!=draft['parent']['failed_call_id']
            or not live.allowance_capacity(parent)['stopped']):
        raise live.LiveBlocked('Frozen input/parent stopped event mismatch')
    prepared=json.loads((ROOT/'docs/evidence/development-approval-preparation-v1/binding.json').read_text())
    if (assistant.PROMPT_HASH!=prepared['prompt_hash']
            or exp.digest(assistant.Answer.model_json_schema())!=prepared['settings']['answer_schema_sha256']
            or config.model!=draft['model'] or config.request_timeout_seconds!=30
            or hashlib.sha256(config.base_url.encode()).hexdigest()!=draft['endpoint_sha256']):
        raise live.LiveBlocked('Model/prompt/schema/configuration drift')
    receipt=ROOT/'.private/azure_development07_diagnostic_allowance_v1.json'
    allowance_id=draft['proposed_allowance_id']
    folder=reg.ROOT/'diagnostics'/allowance_id
    if receipt.exists() or folder.exists():raise live.LiveBlocked('Single-use diagnostic already prepared/attempted; no duplicate grant')
    originals={p:hashlib.sha256(p.read_bytes()).hexdigest() for p in source.iterdir() if p.is_file()}
    with reg.connect() as db:
        prior_allowances=[dict(r) for r in db.execute('SELECT * FROM allowance')]
        prior_calls={r['id']:hashlib.sha256(r['data'].encode()).hexdigest() for r in db.execute('SELECT id,data FROM calls')}
        old_failures=[r['id'] for r in db.execute("SELECT id,status FROM calls WHERE allowance_id=?",(parent.allowance_id,)) if r['status'] not in ('completed','reserved')]
        if old_failures!=[draft['parent']['failed_call_id']]:raise live.LiveBlocked('Additional or changed parent failures; recovery scope insufficient')
        if db.execute('SELECT 1 FROM calls WHERE allowance_id=?',(allowance_id,)).fetchone():raise live.LiveBlocked('Existing diagnostic usage')
    with (reg.ROOT/'backend.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        now=datetime.now(timezone.utc)
        a=live.Approval(provider='azure_openai',allowance_id=allowance_id,confirmed_free_promotional=True,
            approved_model=config.model,approved_endpoint=config.base_url,deployment_model_version=draft['model_version'],
            activated_at=now,expires_at=now+timedelta(hours=1),max_calls=1,max_reserved_tokens=32000,
            chat_completions_supported=True,structured_outputs_supported=True,max_output_tokens_supported=True,
            entitlement_expiry='unknown',eligibility_checked_at=now,
            eligibility_evidence='Current user explicitly confirms valid remaining Azure trial credits and enabled spending protection. User-reported account facts, not independently verified. Trial-only; no upgrade, spending-limit removal or out-of-pocket consent.',
            confirmation_note='Current user explicitly authorizes ONE linked development-07 A diagnostic despite the original HTTP400 stop,1attempt/32000new units/one hour. Preserve parent stop/history, frozen input and settings; zero retries; finish disabled. No other recovery permitted.')
        folder.mkdir(parents=True,exist_ok=False)
        fd=os.open(receipt,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
        with os.fdopen(fd,'w') as out:out.write(a.model_dump_json(indent=2))
        binding={'execution_identity':exp.execution_identity(),'prompt_hash':assistant.PROMPT_HASH,
            'schema_hash':exp.digest(assistant.Answer.model_json_schema()),'parent':draft['parent'],
            'frozen_input':draft['frozen_input'],'authorization_basis':a.confirmation_note,
            'funding':'user-confirmed trial credits and spending protection only; no independent billing verification',
            'activated_at':now.isoformat(),'expires_at':a.expires_at.isoformat()}
        (folder/'binding.json').write_text(json.dumps(binding,indent=2))
        bound=Bound(folder,[('A','generation')],32000)
        result=None
        try:
            with patch.dict(os.environ,{'LIVE_LLM_ENABLED':'true','FREE_ONLY':'true','AZURE_OPENAI_ALLOWANCE_FILE':str(receipt)}),patch.object(live,'reserve',side_effect=bound.reserve),patch.object(live,'call',side_effect=bound.call):
                result=assistant.respond(failed['case']['query'],'A',initial=deepcopy(json.loads(frozen_path.read_text())['retrieval']),
                    run_context={'diagnostic_id':allowance_id,'case_id':'development-07','parent_failed_call_id':draft['parent']['failed_call_id']})
            (folder/'response.json').write_text(json.dumps(result,indent=2))
        finally:
            os.environ['LIVE_LLM_ENABLED']='false'
            if result is None or result['status'] not in exp.COMPLETED:
                with reg.connect() as db:db.execute('UPDATE allowance SET stopped=1 WHERE id=?',(hashlib.sha256(a.model_dump_json().encode()).hexdigest(),))
            with reg.connect() as db:
                history_ok=all(dict(db.execute('SELECT * FROM allowance WHERE id=?',(r['id'],)).fetchone())==r for r in prior_allowances)
                calls_ok=all(hashlib.sha256(db.execute('SELECT data FROM calls WHERE id=?',(rid,)).fetchone()['data'].encode()).hexdigest()==h for rid,h in prior_calls.items())
            record=(result or {}).get('calls',[])
            selected={k:record[-1].get(k) for k in ['http_status','provider_request_id','provider_error_code','provider_error_type','provider_error_parameter','provider_inner_error_code','provider_content_filter_categories','provider_error_message','diagnostic_detail_policy','usage','latency_ms']} if record else {}
            summary={'outcome':result['status'] if result else 'interrupted_or_failed','attempts':len(bound.data['attempts']),
                'diagnostics':selected,'remaining':live.allowance_capacity(a),'expires_at':a.expires_at.isoformat(),
                'parent_stop_preserved':live.allowance_capacity(parent)['stopped'],
                'historical_accounting_unchanged':history_ok and calls_ok,
                'parent_receipt_unchanged':parent_path.read_bytes()==parent_bytes,
                'original_evaluation_artifacts_unchanged':all(hashlib.sha256(p.read_bytes()).hexdigest()==h for p,h in originals.items()),
                'live_disabled':True}
            (folder/'operational-summary.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary))

if __name__=='__main__':main()
