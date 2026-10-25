"""One authorized screening-only probe through the real provider gate. No retries.

No import-time execution; exclusive receipt prevents duplicate activation.
Original stops and interactive capacity are never altered.
"""
from datetime import datetime, timedelta, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
from unittest.mock import patch

from dotenv import dotenv_values
from app.storage import registry as reg
from app.core.config import LiveSettings, azure_base_url
from app.evaluation import experiment as exp
from app.llm import client as live
from app.llm.experiment_settings import identity_settings
from app.rag import assistant
from app.defenses import screening

ROOT = Path(__file__).resolve().parents[2]
RUN_ID = 'azure-development08-screening-minimal-probe-v1'
VERSION = 'azure-gpt5mini-v3-screening-minimal-cap700-probe-v1'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main(*, execute=False, contract_v2=False):
    run_id = 'azure-development08-screening-contract-v2-probe-v1' if contract_v2 else RUN_ID
    version = 'screening-question-source-contract-v2-minimal-cap700-probe-v1' if contract_v2 else VERSION
    os.environ.update(LIVE_LLM_ENABLED='false', FREE_ONLY='true', HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1')
    config = LiveSettings.from_env()
    source = reg.ROOT / 'experiments/azure-development-08-12-stage-v1'
    proposal = json.loads((ROOT / 'docs/evidence/development08-screening-minimal-v3-proposed.json').read_text())
    if any(sha(source / n) != h for n, h in proposal['historical_evidence_sha256'].items()):
        raise live.LiveBlocked('Frozen development-08 artifacts changed')
    failed = json.loads((source / 'case-development-08-C-0.json').read_text())
    frozen = json.loads((source / 'retrieval-development-08-0.json').read_text())['retrieval']
    prepared = json.loads((ROOT / 'docs/evidence/development-approval-preparation-v1/binding.json').read_text())
    expected_prompt = prepared['prompt_hash']
    if contract_v2:
        corrected = json.loads((ROOT / 'docs/evidence/screening-question-source-contract-v2/binding.json').read_text())
        if (screening.PROMPT_VERSION != 'screening-question-source-contract-v2'
                or hashlib.sha256(screening.SCREEN.encode()).hexdigest() != corrected['screening_prompt_sha256']
                or exp.digest(assistant.Screening.model_json_schema()) != corrected['screening_schema_sha256']):
            raise live.LiveBlocked('Approved contract-v2 prompt/schema mismatch')
        expected_prompt = corrected['prompt_hash']
    account = live.Approval.model_validate_json((ROOT / '.private/azure_development07_diagnostic_allowance_v1.json').read_text())
    parent_path = ROOT / '.private/azure-development-08-12-stage-v1-allowance.json'
    parent = live.Approval.model_validate_json(parent_path.read_text())
    saved_env = dotenv_values(ROOT / '.env', interpolate=False)
    root_matches = (bool(config.api_key) and config.api_key == (saved_env.get('AZURE_OPENAI_API_KEY') or '').strip()
        and config.model == (saved_env.get('AZURE_OPENAI_DEPLOYMENT') or '').strip()
        and config.base_url == azure_base_url((saved_env.get('AZURE_OPENAI_ENDPOINT') or '').strip()))
    if not root_matches:
        raise live.LiveBlocked('Effective Azure configuration does not match saved root settings')
    if (not account.confirmed_free_promotional or account.paid_azure_test_authorized
            or not account.eligibility_evidence):
        raise live.LiveBlocked('Existing account evidence does not establish trial-only execution')
    if (config.model != account.approved_model or config.base_url != account.approved_endpoint
            or account.deployment_model_version.replace(' ', '') != 'gpt-5-mini/2025-08-07'
            or config.request_timeout_seconds != 30
            or assistant.PROMPT_HASH != expected_prompt
            or exp.digest(assistant.Screening.model_json_schema()) != prepared['settings']['screening_schema_sha256']
            or exp.digest(assistant.Answer.model_json_schema()) != prepared['settings']['answer_schema_sha256']
            or frozen['hits'] != failed['response']['candidate_evidence']):
        raise live.LiveBlocked('Frozen model/prompt/schema/evidence/settings mismatch')
    old = failed['response']['calls'][0]
    if (old.get('http_status'), old.get('finish_reason'), old.get('response_validation_error')) != (200, 'length', 'empty_content'):
        raise live.LiveBlocked('Recovery is scoped only to the saved length/empty-content screening failure')
    folder = reg.ROOT / 'diagnostics' / run_id
    receipt = ROOT / '.private' / (run_id + '-allowance.json')
    if receipt.exists() or folder.exists():
        raise live.LiveBlocked('Single-use probe already activated; no duplicate capacity or retry')
    with (reg.ROOT / 'backend.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if not live.allowance_capacity(parent)['stopped']:
            raise live.LiveBlocked('Expected parent stop is missing; no recovery applied')
        with reg.connect() as db:
            prior_allowances = [dict(r) for r in db.execute('SELECT * FROM allowance')]
            prior_calls = {r['id']: dict(r) for r in db.execute('SELECT * FROM calls')}
            allowed = {'azure-development-12cases-20261023-v1', 'azure-development07-A-diagnostic-v1', parent.allowance_id}
            if contract_v2:
                prior_result = json.loads((reg.ROOT / 'diagnostics' / RUN_ID / 'response.json').read_text())
                if (prior_result['status'] != 'screening_validation_failed'
                        or json.loads(prior_result['call']['response_content'])['flagged_source_ids'] != ['user_message']):
                    raise live.LiveBlocked('Linked prior invalid-ID screening event mismatch')
                allowed.add(RUN_ID)
            for row in prior_calls.values():
                data = json.loads(row['data'])
                if data.get('error') and data.get('settings', {}).get('provider') == 'azure_openai' and row['allowance_id'] not in allowed:
                    raise live.LiveBlocked('Additional unresolved error outside explicitly linked recovery')
            if any(r['allowance_id'] == run_id for r in prior_calls.values()):
                raise live.LiveBlocked('Existing diagnostic usage; no duplicate grant')
        if not execute:
            print(json.dumps({'preflight_passed': True, 'root_configuration_matches': root_matches,
                'trial_evidence_reused': True, 'parent_stop_present': True,
                'receipt_exists': False, 'provider_attempts': 0, 'activated': False}))
            return
        originals = {p: sha(p) for p in source.iterdir() if p.is_file()}
        private_originals = {p: sha(p) for p in (ROOT / '.private').glob('*.json')}
        now = datetime.now(timezone.utc)
        a = live.Approval(provider='azure_openai', allowance_id=run_id, confirmed_free_promotional=True,
            approved_model=config.model, approved_endpoint=config.base_url,
            deployment_model_version=account.deployment_model_version,
            activated_at=now, expires_at=now + timedelta(hours=1), max_calls=1, max_reserved_tokens=32000,
            chat_completions_supported=True, structured_outputs_supported=True, max_output_tokens_supported=True,
            entitlement_expiry='unknown', eligibility_checked_at=now,
            eligibility_evidence='Reused user confirmation of valid remaining Azure trial credits and enabled spending protection. User-reported, not independently verified. Trial credits only; no subscription upgrade, spending-limit removal or out-of-pocket authorization.',
            confirmation_note=('Current user explicitly approves one development-08 screening-question-source-contract-v2 verification. ' if contract_v2 else 'Current user explicitly approves one development-08 screening-only probe. ') + 'Minimal reasoning, cap700, one attempt/32000 new local units/one hour. Linked recovery of saved length/empty-content and invalid-ID events only. Preserve all parent stops; no answering, retry or batch.')
        identity = {'version': version, 'execution': exp.execution_identity(),
            'model': config.model, 'model_version': a.deployment_model_version,
            'endpoint_sha256': hashlib.sha256(config.base_url.encode()).hexdigest(),
            'settings': identity_settings() | {'configuration_version': version, 'screening_reasoning_effort': 'minimal', 'answering_reasoning_effort': 'not sent'},
            'runner_sha256': sha(Path(__file__)), 'prompt_hash': assistant.PROMPT_HASH,
            'schema_sha256': exp.digest(assistant.Screening.model_json_schema()),
            'frozen_inputs_sha256': proposal['historical_evidence_sha256'],
            'parent_allowance_id': parent.allowance_id, 'parent_call_id': old['call_id'],
            'scored_evaluation': False, 'root_configuration_matches': root_matches,
            'screening_prompt_version': screening.PROMPT_VERSION if contract_v2 else 'original',
            'linked_prior_diagnostic': RUN_ID if contract_v2 else None}
        folder.mkdir(parents=True, exist_ok=False)
        fd = os.open(receipt, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, 'w') as out:
            out.write(a.model_dump_json(indent=2))
        (folder / 'binding.json').write_text(json.dumps({'identity': identity, 'identity_sha256': exp.digest(identity),
            'activated_at': now.isoformat(), 'expires_at': a.expires_at.isoformat(), 'authorization_basis': a.confirmation_note}, indent=2))
        result = {'case_id': 'development-08', 'stage': 'screening_only', 'scored_evaluation': False,
                  'status': 'interrupted_or_failed', 'schema_valid': False, 'screening': None, 'call': None}
        try:
            with patch.dict(os.environ, LIVE_LLM_ENABLED='true', FREE_ONLY='true', AZURE_OPENAI_ALLOWANCE_FILE=str(receipt)):
                ids = live.reserve(1, 32000, metadata={'diagnostic_id': run_id, 'case_id': 'development-08',
                    'mode': 'C_screening_only', 'identity_sha256': exp.digest(identity),
                    'screening_prompt_version': screening.PROMPT_VERSION if contract_v2 else 'original'})
                try:
                    raw, trace = live.call([{'role': 'developer', 'content': assistant.SCREEN},
                        {'role': 'user', 'content': json.dumps({'question': failed['case']['query'], 'sources': frozen['hits']}, ensure_ascii=True)}],
                        assistant.Screening.model_json_schema(), 'screening', ids[0], screening_reasoning_effort='minimal')
                    result['call'] = trace
                    decision = assistant.Screening.model_validate_json(raw)
                    if set(decision.flagged_source_ids) - {h['id'] for h in frozen['hits']}:
                        raise ValueError('unknown_source_ids')
                    result.update(status='valid_screening_json', schema_valid=True, screening=decision.model_dump())
                except live.ModelFailure as exc:
                    result.update(status='provider_or_response_error', call=exc.record, error=exc.category)
                except ValueError:
                    result.update(status='screening_validation_failed', error='invalid_screening_decision')
        finally:
            os.environ['LIVE_LLM_ENABLED'] = 'false'
            fingerprint = hashlib.sha256(a.model_dump_json().encode()).hexdigest()
            with reg.connect() as db:
                db.execute('INSERT OR IGNORE INTO allowance VALUES(?,?,?,1)', (fingerprint, 0, 0))
                db.execute('UPDATE allowance SET stopped=1 WHERE id=?', (fingerprint,))
                unchanged = all(dict(db.execute('SELECT * FROM allowance WHERE id=?', (r['id'],)).fetchone()) == r for r in prior_allowances)
                unchanged &= all(dict(db.execute('SELECT * FROM calls WHERE id=?', (rid,)).fetchone()) == r for rid, r in prior_calls.items())
            (folder / 'response.json').write_text(json.dumps(result, indent=2))
            summary = {'status': result['status'], 'schema_valid': result['schema_valid'],
                'call': result['call'], 'capacity': live.allowance_capacity(a), 'expires_at': a.expires_at.isoformat(),
                'historical_accounting_preserved': unchanged,
                'parent_stop_preserved': live.allowance_capacity(parent)['stopped'],
                'historical_artifacts_preserved': all(sha(p) == h for p, h in originals.items()),
                'prior_private_receipts_preserved': all(sha(p) == h for p, h in private_originals.items()),
                'live_disabled': True, 'scored_evaluation': False}
            (folder / 'summary.json').write_text(json.dumps(summary, indent=2))
            print(json.dumps({k: v for k, v in summary.items() if k != 'call'}))


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--contract-v2', action='store_true', help='Use separately authorized question/source contract-v2 verification')
    parser.add_argument('--execute', action='store_true', help='Activate and execute exactly one authorized probe')
    try:
        args = parser.parse_args()
        main(execute=args.execute, contract_v2=args.contract_v2)
    except Exception as exc:
        # Never emit exception values or tracebacks containing credential/request data.
        print(json.dumps({'blocked_or_interrupted': True, 'exception_type': type(exc).__name__,
            'blocking_check': str(exc) if isinstance(exc, live.LiveBlocked) else 'See sanitized failure type; no provider retry',
            'location': 'backend/scripts/run_development08_screening_probe.py'}))
        raise SystemExit(1)
