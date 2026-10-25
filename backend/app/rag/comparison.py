"""User-triggered benign paired comparison, not an automatically graded benchmark."""
from copy import deepcopy
from time import perf_counter
from app.rag.retrieval import search
from app.rag.assistant import respond, PROMPT_HASH
from app.llm import client as live

COMPLETED = {'answered', 'conflict', 'insufficient_evidence', 'policy_blocked'}


def compare(question, request_id):
    started = perf_counter()
    result = {'status': 'not_started', 'question': question, 'results': {},
              'initial_evidence': None, 'prompt_hash': PROMPT_HASH,
              'review_status': 'unreviewed', 'output_origin': 'application_execution', 'scope': 'benign_interactive_comparison',
              'planned_maximum_calls': 4, 'planned_maximum_units': 128000}
    try:
        approval = live.approval()
        capacity = live.allowance_capacity(approval)
        if capacity['stopped'] or capacity['remaining_calls'] < 4 or capacity['remaining_reserved_tokens'] < 128000:
            raise live.LiveBlocked('A/B/C comparison needs 4 available calls and 128000 units in an unstopped allowance')
        from app.evaluation.comparison_provenance import capture
        result['review_provenance'] = capture(PROMPT_HASH)
        result['source_request_id'] = request_id
        initial = search(question)
        live.validate_interactive_input(question, initial['hits'])
        result['initial_evidence'] = initial
        if not initial['hits']:
            result.update(status='insufficient_evidence', error='No active evidence found; no model calls made.')
            return result
        # API holds registry lock across this unit: another app request cannot
        # consume its capacity between preflight and per-mode reservations.
        for mode in 'ABC':
            response = respond(question, mode, initial=deepcopy(initial),
                               run_context={'client_request_id':request_id, 'comparison_mode':mode})
            result['results'][mode] = response
            if response['status'] not in COMPLETED:
                result.update(status='partial', error='Comparison stopped on an operational error; later modes were not executed.')
                return result
        result['status'] = 'completed'
    except live.LiveBlocked as exc:
        result.update(status='live_blocked', error=str(exc))
    except Exception:
        result.update(status='operational_error', error='Local comparison preparation failed; inspect document state. No automatic retry.')
    finally:
        result['latency_ms'] = (perf_counter() - started) * 1000
        result['not_executed_modes'] = [m for m in 'ABC' if m not in result['results']]
        from app.evaluation.compatibility import digest
        result['source_record_binding'] = digest(result)
    return result
