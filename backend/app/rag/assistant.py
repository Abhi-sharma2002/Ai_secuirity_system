"""Shared A/B/C service. Runtime never imports a fake provider or evaluator labels."""
import hashlib
import os
from time import perf_counter
from uuid import uuid4
from app.rag.retrieval import search
from app.defenses import baseline, instruction_separation, screening, output_screening
from app.defenses.baseline import GROUND
from app.defenses.instruction_separation import SEPARATION
from app.defenses.screening import SCREEN, Screening
from app.defenses.contracts import Answer
from app.defenses.public_test_cards import POLICY_HASH, supported_numbers
from app.llm import client as live


PROMPT_HASH = hashlib.sha256((GROUND + SEPARATION + SCREEN + output_screening.VERSION + POLICY_HASH).encode()).hexdigest()


def messages(mode, question, evidence):
    build = instruction_separation.messages if mode in {'B', 'C'} else baseline.messages
    return build(question, evidence)


def respond(question, mode, *, initial=None, snapshot_items=None, run_context=None, _evaluation_call=None):
    # Only the explicit local evaluation adapter can supply this call boundary.
    # Interactive API callers never pass it, even if EVAL_MODE is set.
    if _evaluation_call is not None and (os.getenv('EVAL_MODE') != '1' or initial is None):
        raise ValueError('Evaluation calls require EVAL_MODE=1 and supplied retrieval')
    start = perf_counter()
    result = {'request_id': str(uuid4()), 'mode': mode, 'question': question, 'status': 'error',
        'answer': '', 'references': [], 'candidate_evidence': [], 'supplied_evidence': [],
        'reservation_units': 0, 'reservation_ids': [], 'calls': [], 'screening': None, 'prompt_hash': PROMPT_HASH, 'snapshot': [], 'omitted_ids': []}
    result['defense_versions'] = {'grounding': baseline.PROMPT_VERSION,
        'separation': instruction_separation.PROMPT_VERSION if mode in {'B', 'C'} else None,
        'output_screening': output_screening.VERSION if mode == 'C' else None}
    try:
        retrieval = search(question, snapshot_items) if initial is None else initial
        evidence = retrieval['hits']
        result.update(candidate_evidence=evidence, snapshot=retrieval['snapshot'], omitted_ids=retrieval['omitted_ids'])
        if not evidence and mode != 'C':
            result.update(status='insufficient_evidence', answer='No active evidence was retrieved.')
            return result
        if _evaluation_call is None:
            live.validate_interactive_input(question, evidence)
            # Failed/unused interactive reservations are not refunded.
            calls = live.reserve(2 if mode == 'C' else 1, 64_000 if mode == 'C' else 32_000, metadata={'request_id': result['request_id'], 'mode': mode, **(run_context or {})})
            result.update(reservation_units=64_000 if mode == 'C' else 32_000, reservation_ids=calls)
        else:
            calls = [None, None] if mode == 'C' else [None]
        if mode == 'C':
            if _evaluation_call is None:
                evidence = screening.apply(question, evidence, calls, result)
            else:
                evidence = screening.apply(question, evidence, calls, result, _evaluation_call=_evaluation_call)
            if evidence is None:
                return result
        result['supplied_evidence'] = evidence
        if not evidence:
            result.update(status='insufficient_evidence', answer='No usable evidence remains after screening.')
            return result
        call = live.call if _evaluation_call is None else _evaluation_call
        raw, trace = call(messages(mode, question, evidence), Answer.model_json_schema(), 'generation', calls[-1])
        result['calls'].append(trace)
        answer = Answer.model_validate_json(raw)
        lookup = {h['id']: h for h in evidence}
        if set(answer.source_ids) - lookup.keys() or (answer.status in {'answered', 'conflict'} and not answer.source_ids):
            result.update(status='invalid_citations', error='Model returned missing or unknown source IDs')
            return result
        if mode == 'C' and output_screening.contains_payment_card(answer.answer, allowed_numbers=supported_numbers(evidence)):
            result.update(status='policy_blocked', answer='The answer was withheld because it contained a possible payment-card number.',
                          output_screening={'version': output_screening.VERSION, 'blocked': True, 'reason': 'payment_card_pattern',
                                            'candidate_answer_for_local_review': answer.model_dump()})
            return result
        if mode == 'C':
            result['output_screening'] = {'version': output_screening.VERSION, 'blocked': False}
        result.update(status=answer.status, answer=answer.answer,
                      references=[lookup[i] for i in answer.source_ids], citation_check='IDs validated; semantic support requires review')
    except live.LiveBlocked as exc:
        result.update(status='live_blocked', error=str(exc))
    except live.ModelFailure as exc:
        result['calls'].append(exc.record)
        result.update(status='llm_error', error=exc.category)
    except Exception:
        if _evaluation_call is not None:
            raise
        result.update(status='operational_error', error='Retrieval, model response, or schema failed; no fallback answer generated')
    finally:
        if _evaluation_call is None and result['status'] in {'screening_error', 'llm_error', 'operational_error', 'invalid_citations'}:
            live.stop_paid_test_on_error(result['reservation_ids'])
        result['latency_ms'] = (perf_counter() - start) * 1000
    return result
