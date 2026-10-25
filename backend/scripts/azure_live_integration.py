"""Single-use Azure baseline, then source-reviewed paired development-02 A/B/C.

Nothing runs on import. --activate-baseline requires an operator-confirmed Azure
approval draft. --paired requires a successful baseline and an explicit source
review. Together they permit <=5 provider attempts and <=160000 local units.
"""
from app.llm.experiment_settings import identity_settings
import argparse
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import time
from unittest.mock import patch

from app.storage import registry as reg
from app.core.config import LiveSettings
from app.evaluation import experiment as exp
from app.llm import client as live
from app.rag import assistant

BASELINE = 'azure-development-02-A-v1'
PAIRED = 'azure-development-02-ABC-v1'


def write(path, value):
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(value, indent=2))
    temporary.replace(path)


def identity():
    return {'execution': exp.execution_identity(), 'prompt_hash': assistant.PROMPT_HASH,
            'manifest_sha256': hashlib.sha256((exp.DATASET/'manifest.json').read_bytes()).hexdigest(),
            'annotations_sha256': hashlib.sha256((exp.DATASET/'annotations.json').read_bytes()).hexdigest(),
            'snapshot_sha256': hashlib.sha256((exp.DATASET/'snapshot.json').read_bytes()).hexdigest(),
            'semantic_rules': exp.semantics.snapshot(),
            'scoring_sha256': hashlib.sha256(exp.SCORING_SPEC.read_bytes()).hexdigest()}


def activate(config):
    """Activate confirmed terms once; never create evidence or raise ceilings."""
    values = json.loads(config.allowance_file.read_text())
    if values.get('paid_azure_test_authorized') or not config.free_only:
        raise live.LiveBlocked('Standing trial-credit-only scope forbids paid allowance activation')
    if values.get('activated_at') is not None:
        raise live.LiveBlocked('Existing activation; no renewal or retry')
    now = datetime.now(timezone.utc)
    values.update(activated_at=now, expires_at=now+timedelta(hours=1))
    a = live.Approval.model_validate(values)
    used = live.allowance_capacity(a)
    if (a.provider != 'azure_openai' or a.approved_model != config.model
            or a.approved_endpoint != config.base_url or not (a.confirmed_free_promotional or a.paid_azure_test_authorized)
            or (not a.paid_azure_test_authorized and not a.eligibility_evidence) or not a.deployment_model_version
            or (not a.paid_azure_test_authorized and a.eligibility_checked_at is None) or a.entitlement_expiry is None
            or not all((a.chat_completions_supported, a.structured_outputs_supported, a.max_output_tokens_supported))):
        raise live.LiveBlocked('Operator-confirmed Azure eligibility, endpoint/deployment/model and capabilities required')
    if used['stopped']:
        raise live.LiveBlocked('Existing stop or activation; no renewal, retry or bypass')
    if (used['remaining_calls'], used['remaining_reserved_tokens']) != (5, 160000):
        raise live.LiveBlocked('Draft must authorize exactly five additional calls / 160000 local units')
    if not a.paid_azure_test_authorized and (a.eligibility_checked_at.tzinfo is None or a.eligibility_checked_at > now):
        raise live.LiveBlocked('Invalid eligibility check time')
    active = a
    if isinstance(active.entitlement_expiry, datetime) and (
            active.entitlement_expiry.tzinfo is None or active.entitlement_expiry < active.expires_at):
        raise live.LiveBlocked('Actual Azure entitlement does not cover the one-hour local window')
    pending = config.allowance_file.with_suffix('.activation-tmp')
    fd = os.open(pending, os.O_WRONLY|os.O_CREAT|os.O_EXCL, 0o600)
    with os.fdopen(fd, 'w') as output:
        output.write(active.model_dump_json(indent=2))
    os.replace(pending, config.allowance_file)
    return active


class Bound:
    """Preserve real gate/transport; add order, pacing and exclusive trace bounds."""
    def __init__(self, folder, order, max_units, *, clock=None, sleep=None):
        self.folder, self.order, self.max_units = folder, order, max_units
        self.original_call, self.original_reserve = live.call, live.reserve
        self.ids = {}
        self.last_completed = None
        self.clock, self.sleep = clock or time.monotonic, sleep or time.sleep
        self.data = {'attempts': [], 'reserved_calls': 0, 'reserved_units': 0,
                     'outcome': 'interrupted_or_in_progress', 'provider': 'azure_openai',
                     'pacing_seconds_after_completion': 65}

    def save(self):
        write(self.folder/'integration-diagnostics.json', self.data)

    def reserve(self, calls, units, metadata=None):
        mode = (metadata or {}).get('mode')
        expected = (2, 64000) if mode == 'C' else (1, 32000)
        if mode not in ('A', 'B', 'C') or (calls, units) != expected:
            raise live.LiveBlocked('Unexpected reservation shape')
        if self.data['reserved_calls']+calls > len(self.order) or self.data['reserved_units']+units > self.max_units:
            raise live.LiveBlocked('Authorized integration ceiling reached')
        ids = self.original_reserve(calls, units, metadata)
        self.ids.update({rid: mode for rid in ids})
        self.data['reserved_calls'] += calls
        self.data['reserved_units'] += units
        self.save()
        return ids

    def call(self, messages, schema, stage, reservation):
        index = len(self.data['attempts'])
        mode = self.ids.get(reservation)
        if index >= len(self.order) or (mode, stage) != self.order[index]:
            raise live.LiveBlocked('Unexpected provider order; no request')
        if self.last_completed is not None:
            while (remaining := self.last_completed+65-self.clock()) > 0:
                self.sleep(min(remaining, 60))
        attempt = {'mode': mode, 'stage': stage, 'reservation': reservation,
                   'outcome': 'interrupted_or_unknown', 'response': None, 'record': None}
        self.data['attempts'].append(attempt)
        self.save()
        started = time.perf_counter()
        try:
            raw, record = self.original_call(messages, schema, stage, reservation)
            attempt.update(outcome='returned', response=json.loads(raw), record=record)
            return raw, record
        except live.ModelFailure as exc:
            attempt.update(outcome=exc.category, record=exc.record)
            raise
        except live.LiveBlocked:
            attempt['outcome'] = 'blocked_before_provider'
            raise
        finally:
            self.last_completed = self.clock()
            attempt['boundary_latency_ms'] = (time.perf_counter()-started)*1000
            self.save()


def execute(paired=False, source_review_note=None):
    config = LiveSettings.from_env()
    if config.enabled or not config.free_only or not config.api_key or not config.model or not config.base_url:
        raise live.LiveBlocked('Start live-disabled with actual Azure configuration and FREE_ONLY=true')
    if config.request_timeout_seconds != 30:
        raise live.LiveBlocked('Keep the authorized 30-second request limit')
    data = exp.load()
    # Existing snapshot only. No index creation, benchmark mutation or model download.
    snapshot = json.loads((exp.DATASET/'snapshot.json').read_text())
    if (snapshot['dataset_hash'] != exp.digest(data) or snapshot['configuration'] != exp.indexer.index_configuration()
            or snapshot.get('parser_version') != exp.PARSER_VERSION
            or snapshot.get('chunk_size') != exp.settings.chunk_size
            or snapshot.get('chunk_overlap') != exp.settings.chunk_overlap):
        raise live.LiveBlocked('Frozen snapshot identity mismatch')
    case = next(c for c in data['cases'] if c['case_id'] == 'development-02')
    run_id = PAIRED if paired else BASELINE
    folder = reg.ROOT/'experiments'/run_id
    if folder.exists():
        raise live.LiveBlocked('Single-use run already exists; preserve partial results, do not retry')
    if paired:
        baseline = json.loads((reg.ROOT/'experiments'/BASELINE/'integration-diagnostics.json').read_text())
        if (baseline['outcome'] != 'answered' or not source_review_note or len(source_review_note.strip()) < 10
                or baseline['identity'] != identity()):
            raise live.LiveBlocked('Successful same-identity baseline and explicit source-support review required')
        initial = baseline['initial_retrieved_evidence']
        a = live.Approval.model_validate_json(config.allowance_file.read_text())
        if hashlib.sha256(a.model_dump_json().encode()).hexdigest() != baseline['approval_fingerprint']:
            raise live.LiveBlocked('Baseline approval changed; no paired run')
        order, units = [('A','generation'), ('B','generation'), ('C','screening'), ('C','generation')], 128000
    else:
        if (reg.ROOT/'experiments'/PAIRED).exists():
            raise live.LiveBlocked('Paired history already exists')
        initial = exp.search(case['query'], [snapshot['items'][f] for f in case['fixtures']])
        if not initial['hits']:
            raise live.LiveBlocked('No actual fictional evidence retrieved')
        order, units = [('A', 'generation')], 32000
        a = activate(config)
    folder.mkdir(parents=True, exist_ok=False)
    bound = Bound(folder, order, units)
    if paired:
        # Also preserve the minimum gap across the two separately reviewed commands.
        bound.last_completed = bound.clock()
    bound.data.update(identity=identity(), case_id='development-02', question=case['query'],
                      initial_retrieved_evidence=deepcopy(initial), expires_at=a.expires_at.isoformat(),
                      approval_fingerprint=hashlib.sha256(a.model_dump_json().encode()).hexdigest(),
                      source_review_note=source_review_note, source_review_role='agent_or_operator',
                      accounting_before=live.allowance_capacity(a), defense_effectiveness_claim=False)
    bound.save()
    try:
        with patch.dict(os.environ, {'LIVE_LLM_ENABLED': 'true', 'FREE_ONLY': 'false' if a.paid_azure_test_authorized else 'true'}), \
             patch.object(live, 'reserve', side_effect=bound.reserve), patch.object(live, 'call', side_effect=bound.call):
            live.approval()  # Real gate, never replaced.
            if paired:
                def frozen_search(question, items):
                    if question != case['query'] or items != [snapshot['items'][f] for f in case['fixtures']]:
                        raise live.LiveBlocked('Paired question or retrieval scope changed')
                    return deepcopy(initial)
                with patch.object(exp, 'load', return_value=data), patch.object(exp, 'prepare', return_value=snapshot), \
                     patch.object(exp, 'search', side_effect=frozen_search):
                    exp.run(run_id, 'development', 'paired', 1, 5, True, case_id='development-02')
                bound.data['outcome'] = 'completed_review_pending'
            else:
                specification = {'experiment_id': run_id, 'protocol': 'baseline',
                    'case_id': 'development-02', 'repetitions': 1,
                    'workload': {'case_attempts': 1, 'selected_case_ids': ['development-02']},
                    'settings': {'provider': config.provider, 'model': config.model,
                        'base_url': config.base_url, 'api': 'azure_openai_v1_chat_completions',
                        **identity_settings()},
                    'execution_identity': bound.data['identity'], 'holdout_status': 'exposed_for_audit',
                    'scoring_rules': 'phase12-approved-v1', 'semantic_rules': exp.semantics.snapshot(),
                    'untouched_holdout': False}
                write(folder/'experiment.json', {'specification': specification})
                result = assistant.respond(case['query'], 'A', initial=deepcopy(initial),
                    run_context={'experiment_id': run_id, 'case_id': 'development-02', 'protocol': 'baseline'})
                write(folder/'baseline-response.json', result)
                write(folder/'case-development-02-A-0.json', {'experiment_id': run_id,
                    'protocol': 'baseline', 'case_id': 'development-02', 'mode': 'A', 'repetition': 0,
                    'specification_hash': exp.digest(specification), 'case': case, 'response': result,
                    'output_origin': 'application_execution', 'exposed': None, 'answering_exposed': None,
                    'semantic_review': exp.semantics.criteria(specification['semantic_rules'], case['case_id']),
                    'judgment': {'attack_success': None, 'task_success': None, 'quality': None,
                                 'reviewer': None, 'rubric_version': exp.RUBRIC}})
                bound.data['outcome'] = result['status']
                if result['status'] != 'answered':
                    raise live.LiveBlocked('Baseline failed or did not answer; stop, no paired run')
    except BaseException:
        with reg.connect() as db:
            db.execute('UPDATE allowance SET stopped=1 WHERE id=?',
                       (hashlib.sha256(a.model_dump_json().encode()).hexdigest(),))
        bound.data['outcome_before_stop'] = bound.data['outcome']
        bound.data['outcome'] = 'stopped_no_retry'
        raise
    finally:
        bound.data['accounting_after'] = live.allowance_capacity(a)
        bound.save()
    return {'run_id': run_id, 'outcome': bound.data['outcome'],
            'attempts': len(bound.data['attempts']), 'expires_at': a.expires_at.isoformat(),
            'capacity': live.allowance_capacity(a)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    choice = parser.add_mutually_exclusive_group(required=True)
    choice.add_argument('--activate-baseline', action='store_true')
    choice.add_argument('--paired', action='store_true')
    parser.add_argument('--source-review-note')
    args = parser.parse_args()
    # Caller stops only identified project services first. Lock refusal never kills services.
    with (reg.ROOT/'backend.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX|fcntl.LOCK_NB)
        print(json.dumps(execute(args.paired, args.source_review_note)))


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print(json.dumps({'outcome': 'blocked_or_stopped_no_retry', 'exception_type': type(exc).__name__}))
        raise SystemExit(1)
