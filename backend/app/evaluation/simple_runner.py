"""Local A/B/C adapter. Provider evaluation remains disabled by standing scope.

Only ask() is a public entry point. This module never reads receipts, writes
accounting, routes to Azure, retries a request or patches shared module globals.
"""
from copy import deepcopy
import hashlib
import json
import math
import os
from threading import RLock
from time import perf_counter, sleep

from pydantic import Field, ValidationError

from app.evaluation.simple_config import EvaluationError, ROOT, load_config
from app.evaluation.simple_index import collection_path, digest, embedding_identity
from app.defenses.screening import Screening
from app.llm.diagnostics import sanitize
from app.rag.assistant import respond

DATASET = ROOT / 'backend/benchmark_v3'
STORE = ROOT / '.cache/evaluation_v3'
_CACHE = {}
_CACHE_LOCK = RLock()
_CALL_LOCK = RLock()
_LAST_CALL = {'started': None, 'finished': None}


class _ScreeningWithReasons(Screening):
    question_reason: str = Field(description='Explain a flagged question; empty string when question_flagged is false.')
    source_reasons: dict[str, str] = Field(description='A nonempty reason for each flagged source ID, with exactly the flagged_source_ids as keys.')


def _model_call(messages, schema, stage, config):
    # Implementing an adapter is not authorization to send evaluation traffic.
    # Tests replace this boundary with explicit synthetic responses only.
    raise EvaluationError('Provider evaluation is disabled by the standing project scope; no request sent.')


def _pace_call():
    now = perf_counter()
    wait = max(0.0,
               0.0 if _LAST_CALL['started'] is None else _LAST_CALL['started'] + 3.1 - now,
               0.0 if _LAST_CALL['finished'] is None else _LAST_CALL['finished'] + 1.0 - now)
    if wait:
        sleep(wait)
    _LAST_CALL['started'] = perf_counter()


def _invoke_model(messages, schema, stage, config):
    # Pace each screening/generation call, including C's two separate requests.
    # No retries or fallback dispatches; the real provider boundary remains disabled.
    with _CALL_LOCK:
        _pace_call()
        try:
            return _model_call(messages, schema, stage, config)
        finally:
            _LAST_CALL['finished'] = perf_counter()


def _manifest():
    try:
        raw = (DATASET / 'manifest.json').read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        if digest != (DATASET / 'manifest.sha256').read_text().strip():
            raise EvaluationError('Evaluation manifest hash mismatch')
        data = json.loads(raw)
        if data['dataset_version'] != 'fictional-v3':
            raise EvaluationError('Expected the v3 evaluation dataset')
        return data, digest
    except (OSError, KeyError, json.JSONDecodeError):
        raise EvaluationError('Missing or invalid v3 evaluation manifest') from None


def _identity(config, manifest_sha):
    try:
        identity = json.loads((STORE / 'identity.json').read_text())
    except (OSError, json.JSONDecodeError):
        raise EvaluationError('Local evaluation index is not prepared; interactive storage was not used.') from None
    config_sha = digest(config)
    if (not isinstance(identity, dict) or identity.get('manifest_sha256') != manifest_sha
            or identity.get('config_sha256') != config_sha
            or identity.get('embedding_sha256') != embedding_identity()
            or not isinstance(identity.get('generation'), str) or not identity['generation']):
        raise EvaluationError('Local evaluation index identity does not match the dataset and configuration')
    return identity


def _retrieve(question, doc_ids, config, identity):
    # Step 6 will prepare this isolated store; never create/use the app's store.
    index_path = collection_path(STORE, identity)
    if not index_path.is_dir():
        raise EvaluationError('Local evaluation Chroma index is missing')
    import chromadb
    from app.rag.embeddings import ProjectEmbeddings
    client = chromadb.PersistentClient(path=str(index_path),
                                      settings=chromadb.Settings(anonymized_telemetry=False))
    collection = client.get_collection('benchmark_v3', embedding_function=None)
    metadata = collection.metadata or {}
    if any(metadata.get(key) != value for key, value in identity.items()):
        raise EvaluationError('Local evaluation collection identity mismatch')
    if not collection.count():
        raise EvaluationError('Local evaluation collection is empty')
    found = collection.query(query_embeddings=[ProjectEmbeddings().embed_query(question)],
                             n_results=min(config['top_k'], collection.count()),
                             where={'document_id': {'$in': list(doc_ids)}},
                             include=['documents', 'metadatas', 'distances'])
    rows = [found[key][0] for key in ('ids', 'documents', 'metadatas', 'distances')]
    if len({len(row) for row in rows}) != 1:
        raise EvaluationError('Mismatched evaluation retrieval lengths')
    hits = []
    for cid, text, meta, distance in zip(*rows):
        if (not isinstance(cid, str) or not cid or not isinstance(text, str) or not text.strip()
                or meta.get('document_id') not in doc_ids
                or not math.isfinite(distance)
                or hashlib.sha256(text.encode()).hexdigest() != meta.get('chunk_sha256')
                or meta.get('chunk_size') != config['chunk_size']
                or meta.get('chunk_overlap') != config['chunk_overlap']):
            raise EvaluationError('Invalid evaluation chunk content or provenance')
        hits.append({'id': cid, 'text': text, 'document_id': meta['document_id'],
                     'filename': meta['source'], 'sha256': meta['fixture_sha256'],
                     'page': meta.get('page', 0), 'section': meta.get('section', ''), 'distance': distance})
    if len({h['id'] for h in hits}) != len(hits):
        raise EvaluationError('Duplicate evaluation chunk IDs')
    return sorted(hits, key=lambda hit: (hit['distance'], hit['id']))


def _install_retrieval(question, doc_ids, config, identity, hits):
    """Restore this run's persisted case evidence before any mode is dispatched."""
    with _CACHE_LOCK:
        _CACHE.clear()
        _CACHE.update(key=(question, tuple(sorted(doc_ids))),
                      signature=json.dumps({'config': config, 'index': identity}, sort_keys=True),
                      hits=deepcopy(hits), modes=set())


def _shared_retrieval(mode, question, doc_ids, config, manifest_sha):
    identity = _identity(config, manifest_sha)
    key = question, tuple(sorted(doc_ids))
    signature = json.dumps({'config': config, 'index': identity}, sort_keys=True)
    with _CACHE_LOCK:
        if _CACHE.get('key') != key or mode in _CACHE.get('modes', set()):
            _CACHE.clear()
            hits = _retrieve(question, key[1], config, identity)
            _CACHE.update(key=key, signature=signature, hits=deepcopy(hits), modes=set())
        elif _CACHE['signature'] != signature:
            raise EvaluationError('Evaluation inputs changed during the A/B/C comparison')
        _CACHE['modes'].add(mode)
        return deepcopy(_CACHE['hits'])


def _error_text(exc):
    if isinstance(exc, EvaluationError):
        return str(exc)
    if isinstance(exc, ValidationError):
        # str(ValidationError) includes raw model input. Retain locations/types only.
        issues = exc.errors(include_input=False, include_context=False, include_url=False)
        fields = {'status', 'answer', 'source_ids', 'question_flagged', 'flagged_source_ids',
                  'reason_codes', 'question_reason', 'source_reasons'}
        locations = ['.'.join(str(part) if type(part) is int or part in fields else '[field]'
                              for part in e['loc']) + ' (' + e['type'] + ')' for e in issues]
        return 'Invalid model response schema: ' + ', '.join(locations)
    # Arbitrary parser/SDK exception prose may echo keys, fragments or headers.
    detail = sanitize(str(exc), os.getenv('OPENROUTER_API_KEY', ''))
    return f'{type(exc).__name__}: {detail}'


def ask(mode: str, question: str, doc_ids: list[str]) -> dict:
    started = perf_counter()
    result = {'answer': '', 'sources': [], 'retrieved_chunks': [],
              'kept_chunk_ids': [], 'removed_chunk_ids': [], 'screen_reasons': {},
              'question_flagged': False, 'blocked': False, 'latency_s': 0.0, 'error': ''}
    decision = None
    try:
        if os.getenv('EVAL_MODE') != '1':
            raise EvaluationError('Evaluation adapter requires EVAL_MODE=1')
        if mode not in {'A', 'B', 'C'}:
            raise EvaluationError('Evaluation mode must be A, B or C')
        if not isinstance(question, str) or not question.strip():
            raise EvaluationError('Evaluation question must be a nonempty string')
        if not isinstance(doc_ids, list) or any(not isinstance(d, str) or not d for d in doc_ids) or len(set(doc_ids)) != len(doc_ids):
            raise EvaluationError('Evaluation doc_ids must be a list of unique document IDs')
        config = load_config()
        data, manifest_sha = _manifest()
        fixtures = {f['fixture_id']: f for f in data['fixtures']}
        if not set(doc_ids) <= fixtures.keys():
            raise EvaluationError('Evaluation document ID is absent from the v3 manifest')
        if not doc_ids:
            raise EvaluationError('No evaluation documents were selected; no request sent.')
        hits = _shared_retrieval(mode, question, doc_ids, config, manifest_sha)
        result['retrieved_chunks'] = deepcopy(hits)
        if any(h['sha256'] != fixtures[h['document_id']]['sha256'] for h in hits):
            raise EvaluationError('Retrieved fixture hash differs from the v3 manifest')

        def call(messages, schema, stage, _unused_reservation):
            nonlocal decision
            wire_schema = _ScreeningWithReasons.model_json_schema() if stage == 'screening' else schema
            raw, trace = _invoke_model(messages, wire_schema, stage, config)
            if stage == 'screening':
                candidate = _ScreeningWithReasons.model_validate_json(raw)
                ids = {h['id'] for h in hits}
                if (not set(candidate.flagged_source_ids) <= ids
                        or set(candidate.source_reasons) != set(candidate.flagged_source_ids)
                        or any(not reason.strip() for reason in candidate.source_reasons.values())
                        or (candidate.question_flagged and not candidate.question_reason.strip())
                        or (not candidate.question_flagged and candidate.question_reason.strip())):
                    raise EvaluationError('Invalid screening source IDs or per-source/question reasons')
                decision = candidate
                raw = candidate.model_dump_json(exclude={'question_reason', 'source_reasons'})
            return raw, trace

        response = respond(question, mode, initial={'hits': hits, 'snapshot': [], 'omitted_ids': []},
                           _evaluation_call=call)
        result['error'] = response.get('error', '')
        if result['error'] and response['status'] != 'invalid_citations':
            result['error'] = response['status'] + ': ' + str(sanitize(
                result['error'], os.getenv('OPENROUTER_API_KEY', '')))
        if response['status'] not in {'answered', 'conflict', 'insufficient_evidence', 'policy_blocked'}:
            result['error'] = result['error'] or 'Assistant returned an operational error'
        if not result['error']:
            result.update(answer=response['answer'], sources=response['references'],
                          blocked=response['status'] == 'policy_blocked')
            if mode == 'C' and response.get('output_screening', {}).get('blocked'):
                result['screen_reasons']['output'] = response['output_screening']['reason']
                result['screen_reasons']['output_candidate'] = response['output_screening']['candidate_answer_for_local_review']
            # C's additional deterministic check is restricted to evaluation.
            # This withholds output; it does not grade attack adoption or ambiguity.
            markers = [c['canary'] for c in data['cases'] if c['adversarial']] + ['CANARY-LAB-8041']
            if mode == 'C' and not result['blocked'] and any(m.casefold() in result['answer'].casefold() for m in markers):
                result['screen_reasons']['output_candidate'] = {
                    'answer': result['answer'], 'source_ids': [source['id'] for source in result['sources']]}
                result.update(answer='The answer was withheld because it contained a benchmark attack marker.',
                              sources=[], blocked=True)
                result['screen_reasons']['output'] = 'benchmark_attack_marker'
    except Exception as exc:
        result.update(answer='', sources=[], blocked=False, error=_error_text(exc))
    finally:
        if mode == 'C':
            removed = set(decision.flagged_source_ids) if decision is not None else set()
            result['removed_chunk_ids'] = [h['id'] for h in result['retrieved_chunks'] if h['id'] in removed]
            result['kept_chunk_ids'] = [h['id'] for h in result['retrieved_chunks'] if h['id'] not in removed]
            if decision is not None:
                result['question_flagged'] = decision.question_flagged
                result['screen_reasons'].update(question=decision.question_reason, chunks=decision.source_reasons)
        result['latency_s'] = perf_counter() - started
    return result
