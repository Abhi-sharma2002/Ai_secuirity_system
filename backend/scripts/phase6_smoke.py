"""Single-use bounded wrapper around the CURRENT paired experiment runner.
Requires separate authorization, truthful allowance and process-scoped live flag.
Never changes flags, credentials, approvals or budgets. No retries or repairs.
"""
import argparse
import fcntl
import json
import time
from pathlib import Path
from unittest.mock import patch

from app.core.config import LiveSettings
from app.core import registry as reg
from app.evaluation import experiment as exp
from app.rag import assistant
from app.llm import client as live
from scripts import prepare_phase6 as prep


class RequestPacer:
    """Wait after completion so even delayed transport starts stay >=65s apart.

    Each boundary call contains at most one synchronous request, with no retries.
    Its completion is later than its actual request start. Waiting 65s from that
    completion is therefore conservative even when setup/connection time varies.
    """
    interval_seconds = 65.0

    def __init__(self, clock=None, sleep=None):
        self.clock = clock or time.monotonic
        self.sleep = sleep or time.sleep
        self.last_completed = None

    def wait(self):
        start = self.clock()
        if self.last_completed is not None:
            deadline = self.last_completed + self.interval_seconds
            while (remaining := deadline - self.clock()) > 0:
                self.sleep(min(remaining, 60.0))
        return self.clock() - start

    def finished(self):
        self.last_completed = self.clock()


def execute(prepared):
    c = LiveSettings.from_env()
    if not c.free_only or not c.enabled:
        raise live.LiveBlocked('Explicit process-scoped live enablement required after authorization')
    if prepared['case_id']!=prep.CASE_ID or prepared['run_id']!=prep.RUN_ID or prepared['protocol']!='paired':
        raise ValueError('Only the prepared single benign workload is permitted')
    if not prepared['readiness']['local_approval_checks_pass']:
        raise live.LiveBlocked('Prepare a fresh passing readiness artifact after truthful operator confirmation')
    expected = {'maximum_api_calls_without_retries':4, 'conservative_reserved_tokens':128000, 'case_attempts':3}
    if any(prepared['workload'].get(k)!=v for k,v in expected.items()):
        raise ValueError('Prepared workload differs from the fixed ceiling')
    folder=reg.ROOT/'experiments'/prep.RUN_ID
    if folder.exists():
        raise live.LiveBlocked('Single-use smoke: existing result directory cannot be resumed or rerun')
    # The CLI owns backend.lock. A readiness rebuild is OFFLINE, even in the
    # explicitly live child; no provider/reservation/index write is permitted.
    import os
    with patch.dict(os.environ, {'LIVE_LLM_ENABLED':'false'}), \
         patch('socket.socket.connect',side_effect=AssertionError('Readiness network forbidden')), \
         patch.object(live,'call',side_effect=AssertionError('Readiness provider forbidden')), \
         patch.object(live,'reserve',side_effect=AssertionError('Readiness reservation forbidden')):
        current=prep.prepare()
    if (not current['readiness']['local_approval_checks_pass'] or current['identity']!=prepared['identity']
        or current['initial_retrieved_evidence']!=prepared['initial_retrieved_evidence']
        or current['local_budget']['approval_fingerprint']!=prepared['local_budget']['approval_fingerprint']):
        raise live.LiveBlocked('Readiness, identity, approval or initial evidence changed; stop and review offline')
    # Keep identity/evidence immutable during this run. Reuse validated dataset
    # preparation and paired runner; ensure its retrieval is exactly the frozen
    # initial context that was reviewed, without building any new index.
    real_search=exp.search
    def frozen_search(question, items):
        found=real_search(question,items)
        if found!=prepared['initial_retrieved_evidence']:
            raise live.LiveBlocked('Initial evidence changed before execution')
        return found
    original_call,original_reserve=live.call,live.reserve
    pacer = RequestPacer()
    diagnostics={'provenance':'LIVE EXECUTION ONLY; not populated by offline preparation',
                 'provider':'groq','model':c.model,'identity':prepared['identity'],
                 'initial_retrieved_evidence':prepared['initial_retrieved_evidence'],
                 'attempts':[],'reserved_calls':0,'reserved_tokens':0,
                 'pacing':{'minimum_request_start_gap_seconds':65,
                           'mechanism':'wait at least 65 seconds after previous boundary completion'},
                 'accounting_before':prep.accounting(c),'accounting_after':None,'outcome':'started'}
    folder.mkdir(parents=True,exist_ok=False)
    def save():
        (folder/'integration-diagnostics.json').write_text(json.dumps(diagnostics,indent=2))
    save()
    def reserve(calls,tokens,metadata=None):
        if diagnostics['reserved_calls']+calls>4 or diagnostics['reserved_tokens']+tokens>128000:
            raise live.LiveBlocked('Smoke reservation ceiling reached')
        ids=original_reserve(calls,tokens,metadata)
        diagnostics['reserved_calls']+=calls;diagnostics['reserved_tokens']+=tokens
        save()
        return ids
    def call(messages,schema,stage,reservation):
        if len(diagnostics['attempts'])>=4:
            raise live.LiveBlocked('Smoke request ceiling reached')
        waited = pacer.wait()
        row={'stage':stage,'reservation':reservation,'outcome':'interrupted_or_unknown',
             'response':None,'schema_valid':None,'usage':None,'provider_request_id':None,'latency_ms':None,
             'pacing_wait_seconds':waited,'boundary_started_monotonic':pacer.clock()}
        diagnostics['attempts'].append(row);save()
        start=time.perf_counter()
        try:
            raw,record=original_call(messages,schema,stage,reservation)
            row.update(outcome='returned',response=json.loads(raw),usage=record.get('usage'),
                       provider_request_id=record.get('provider_request_id'),client_record=record)
            contract=assistant.Screening if stage=='screening' else assistant.Answer
            try:
                contract.model_validate_json(raw);row['schema_valid']=True
            except Exception:
                row['schema_valid']=False
            return raw,record
        except live.ModelFailure as exc:
            row.update(outcome=exc.category,client_record=exc.record,usage=exc.record.get('usage'),
                       provider_request_id=exc.record.get('provider_request_id'))
            raise
        except live.LiveBlocked:
            row['outcome']='blocked_before_provider';raise
        finally:
            pacer.finished()
            row['latency_ms']=(time.perf_counter()-start)*1000;save()
    try:
        with patch.object(live,'call',side_effect=call),patch.object(live,'reserve',side_effect=reserve), \
             patch.object(exp,'search',side_effect=frozen_search):
            exp.run(prep.RUN_ID,'development','paired',1,5,True,case_id=prep.CASE_ID)
        diagnostics['outcome']='runner_completed_semantic_review_pending'
    except BaseException:
        diagnostics['outcome']='stopped_or_interrupted_no_automatic_retry'
        raise
    finally:
        diagnostics['accounting_after']=prep.accounting(c)
        save()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--prepared',type=Path,required=True)
    p.add_argument('--execute',action='store_true')
    args=p.parse_args()
    if not args.execute:
        p.error('No execution without --execute and separate user authorization')
    # Existing backend must be stopped; do not create or acquire a live service.
    with (reg.ROOT/'backend.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        execute(json.loads(args.prepared.read_text()))


if __name__=='__main__':
    main()
