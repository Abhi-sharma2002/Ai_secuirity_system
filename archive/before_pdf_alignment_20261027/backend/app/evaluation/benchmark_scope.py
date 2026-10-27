"""Explicit benchmark amendment sharing the existing interactive call ledger."""
import fcntl
import hashlib
import json
import os
from pathlib import Path

from app.evaluation.simple_config import EvaluationError, ROOT

SCOPE = ROOT / '.private/azure_benchmark_20261026_v3.json'
JOURNAL = ROOT / '.private/azure_benchmark_20261026_v3_attempts.jsonl'
STOP = ROOT / '.private/azure_benchmark_20261026_v3.stopped'


def stop():
    STOP.touch(exist_ok=True)


def invoke(messages, schema, stage, config):
    from app.core.environment import load_environment
    from app.llm import client
    load_environment()
    try:
        scope = json.loads(SCOPE.read_text())
        approved = client.approval()
        if (scope['authorization'] != 'user-approved-filter-continuation-20261026-v3'
                or scope['max_calls'] != 163 or scope['config'] != config
                or scope['parent_allowance_id'] != approved.allowance_id
                or approved.provider != 'azure_openai' or not approved.confirmed_free_promotional
                or approved.paid_azure_test_authorized
                or scope['manifest_sha256'] != hashlib.sha256(
                    (ROOT / 'backend/benchmark_v3/manifest.json').read_bytes()).hexdigest()):
            raise ValueError()
    except Exception:
        raise EvaluationError('Benchmark authorization or configuration mismatch; no request sent') from None
    JOURNAL.parent.mkdir(parents=True, exist_ok=True)
    with JOURNAL.open('a+') as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        handle.seek(0)
        attempts = [json.loads(line) for line in handle if line.strip()]
        if STOP.exists() or len(attempts) >= scope['max_calls']:
            raise EvaluationError('Benchmark scope stopped or exhausted; no request sent')
        # Shared reservation is durable before transport. No refund on failure.
        reservation = client.reserve(1, 32000, metadata={
            'experiment_id': scope['authorization'], 'stage': stage,
            'benchmark_call': len(attempts) + 1})[0]
        handle.seek(0, 2)
        handle.write(json.dumps({'call_number': len(attempts) + 1,
                                 'reservation': reservation, 'stage': stage}) + '\n')
        handle.flush()
        os.fsync(handle.fileno())
        try:
            raw, trace = client.call(messages, schema, stage, reservation)
            responses = JOURNAL.with_suffix('.responses')
            responses.mkdir(exist_ok=True)
            with (responses / f'{reservation}.json').open('x') as saved:
                json.dump({'call_number': len(attempts) + 1, 'stage': stage,
                           'request_sha256': hashlib.sha256(json.dumps(
                               {'messages': messages, 'schema': schema}, sort_keys=True).encode()).hexdigest(),
                           'response': raw, 'trace': trace}, saved, ensure_ascii=True)
                saved.flush()
                os.fsync(saved.fileno())
            return raw, trace
        except client.ModelFailure as exc:
            if (scope.get('continue_content_filter_errors') is True
                    and exc.record.get('provider_error_code') == 'content_filter'):
                raise EvaluationError('provider_content_filter: Azure refused this request; recorded as an error; no retry') from None
            stop()
            raise EvaluationError('Benchmark provider call failed; scope stopped; consult saved call diagnostics; no retry') from None
        except Exception:
            stop()
            raise EvaluationError('Benchmark provider call failed; scope stopped; consult saved call diagnostics; no retry') from None


def may_continue(error):
    """Only a separately approved provider-filter exception can advance cases."""
    if not error.startswith('provider_content_filter:') or STOP.exists():
        return False
    try:
        scope = json.loads(SCOPE.read_text())
        return (scope.get('authorization') == 'user-approved-filter-continuation-20261026-v3'
                and scope.get('max_calls') == 163
                and scope.get('continue_content_filter_errors') is True)
    except (OSError, ValueError):
        return False
