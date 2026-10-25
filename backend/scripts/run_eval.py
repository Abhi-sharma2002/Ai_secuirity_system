"""Plan or prepare evaluation locally. Live execution is disabled by project scope."""
import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import csv
import fcntl
import hashlib
import json
import os
from pathlib import Path
import sys
from uuid import uuid4

# Set before importing libraries that cache Hugging Face's offline setting.
if __name__ == '__main__':
    os.environ['HF_HUB_OFFLINE'] = '1'
    os.environ['TRANSFORMERS_OFFLINE'] = '1'

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'backend'))

from app.evaluation import simple_runner as assistant
from app.evaluation.simple_config import EvaluationError, load_config
from app.evaluation.simple_index import digest, prepare_store
from app.evaluation.simple_scoring import score_result
from scripts.validate_v3 import validate

OUTPUT = ROOT / 'results'
COLUMNS = ['case_id', 'mode', 'category', 'channel', 'query', 'expected_behavior',
           'retrieved_chunk_ids', 'attack_retrieved', 'kept_chunk_ids', 'removed_chunk_ids',
           'screen_reasons', 'question_flagged', 'blocked', 'answer', 'sources',
           'attack_succeeded', 'task_passed', 'false_positive', 'answer_chunk_removed',
           'citation_correct', 'needs_review', 'latency_s', 'error', 'model']
_FINGERPRINT_FILES = ['backend/scripts/run_eval.py', 'backend/app/evaluation/simple_index.py',
    'backend/app/evaluation/simple_runner.py', 'backend/app/evaluation/simple_config.py',
    'backend/app/evaluation/simple_scoring.py', 'backend/app/ingestion/parsers.py',
    'backend/app/ingestion/chunker.py', 'backend/app/rag/embeddings.py',
    'backend/app/rag/assistant.py', 'docs/SCORING.md', 'docs/SCORING_V3_AMENDMENTS.md']


def _inputs():
    validate()
    config = load_config()
    data, manifest_sha = assistant._manifest()
    return data, config, manifest_sha


def _plan(data, limit=None):
    count = len(data['cases'])
    selected = count if limit is None else min(limit, count)
    smokes = [c['case_id'] for c in data['cases'] if c['case_id'].startswith('v3-')]
    return {'n_cases': count, 'selected_cases': selected, 'selected_records': selected * 3,
            'selected_calls_upper_bound': selected * 4, 'full_records': count * 3,
            'full_calls_upper_bound': count * 4, 'new_case_A_smoke_ids': smokes,
            'full_plus_smokes_calls_upper_bound': count * 4 + len(smokes),
            'small_check_included_by_resume': True, 'automatic_retries': 0,
            'published_default_daily_requests': 50, 'published_requests_per_minute': 20,
            'account_remaining_requests': 'unverified', 'live_execution_enabled': False,
            'provider_requests_made': 0, 'limits_reference': 'https://openrouter.ai/pricing',
            'new_case_A_smokes': 'pending; required before full live evaluation'}


@contextmanager
def _lock(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('a') as handle:
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise EvaluationError('Another local evaluation operation is using these files') from None
        try:
            yield
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)


def _write_json(path, value):
    with path.open('x') as handle:
        json.dump(value, handle, indent=2, ensure_ascii=False)
        handle.write('\n')
        handle.flush()
        os.fsync(handle.fileno())


def _metadata(config, manifest_sha, identity, origin):
    files = _FINGERPRINT_FILES + [str(p.relative_to(ROOT)) for p in sorted((ROOT / 'backend/app/defenses').glob('*.py'))]
    return {'version': 'v3-evaluation-run', 'origin': origin, 'manifest_sha256': manifest_sha,
            'config': config, 'index_identity': identity,
            'implementation_sha256': digest({name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in files})}


def _read_rows(path, data, config):
    if not path.exists():
        raise EvaluationError('Resume requires an existing records.csv')
    cases = {c['case_id']: c for c in data['cases']}
    rows = {}
    with path.open(newline='') as handle:
        reader = csv.DictReader(handle, strict=True)
        if reader.fieldnames != COLUMNS:
            raise EvaluationError('Existing evaluation CSV has a different header')
        for row in reader:
            key = row['case_id'], row['mode']
            if (None in row or any(v is None for v in row.values()) or key in rows
                    or key[0] not in cases or key[1] not in {'A', 'B', 'C'}
                    or row['query'] != cases[key[0]]['query'] or row['model'] != config['model']
                    or not (row['answer'].strip() or row['error'].strip())):
                raise EvaluationError('Existing evaluation rows are malformed, duplicated or incompatible; nothing was overwritten')
            rows[key] = row
    return rows


def _journal(path, case_id, mode, state):
    with path.open('a') as handle:
        handle.write(json.dumps({'case_id': case_id, 'mode': mode, 'state': state}) + '\n')
        handle.flush()
        os.fsync(handle.fileno())


def _started_rows(path):
    started = set()
    if path.exists():
        for line in path.read_text().splitlines():
            event = json.loads(line)
            if event['state'] == 'row_started':
                started.add((event['case_id'], event['mode']))
    return started


def _case_evidence(case, config, identity, output):
    directory = output / 'retrieval'
    directory.mkdir(exist_ok=True)
    path = directory / f'{case["case_id"]}.json'
    header = {'case_id': case['case_id'], 'query': case['query'], 'doc_ids': case['fixtures'], 'index_identity': identity}
    if path.exists():
        stored = json.loads(path.read_text())
        if (any(stored.get(k) != v for k, v in header.items())
                or stored.get('content_sha256') != digest({'hits': stored['hits'], 'error': stored['error']})):
            raise EvaluationError('Saved case retrieval changed; refusing to retrieve different evidence on resume')
        return stored['hits'], stored['error']
    try:
        hits = assistant._retrieve(case['query'], tuple(sorted(case['fixtures'])), config, identity)
        error = ''
    except Exception as exc:
        hits, error = [], assistant._error_text(exc)
    stored = {**header, 'hits': hits, 'error': error, 'content_sha256': digest({'hits': hits, 'error': error})}
    _write_json(path, stored)
    return hits, error


def _error_result(error, hits=None):
    return {'answer': '', 'sources': [], 'retrieved_chunks': hits or [], 'kept_chunk_ids': [],
            'removed_chunk_ids': [], 'screen_reasons': {}, 'question_flagged': False,
            'blocked': False, 'latency_s': 0.0, 'error': error}


def _cell(value):
    if value is None:
        return ''
    if isinstance(value, bool):
        return 'true' if value else 'false'
    if isinstance(value, (list, dict)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    return value


def _record(case, mode, response, config):
    scored = score_result(case, response, mode)
    return {'case_id': case['case_id'], 'mode': mode, 'category': case.get('subtype') or 'benign',
            'channel': case.get('channel') or '', 'query': case['query'],
            'expected_behavior': f'{case["expected_behavior"]}: {case["expected_task"]}',
            'retrieved_chunk_ids': [c['id'] for c in response['retrieved_chunks']],
            'kept_chunk_ids': response['kept_chunk_ids'], 'removed_chunk_ids': response['removed_chunk_ids'],
            'screen_reasons': response['screen_reasons'], 'question_flagged': response['question_flagged'],
            'blocked': response['blocked'] if not response['error'] else False,
            'answer': response['answer'], 'sources': response['sources'], **scored,
            'latency_s': response['latency_s'], 'error': response['error'], 'model': config['model']}


def _run(data, config, manifest_sha, *, limit=None, resume=False, output=OUTPUT, origin='application_execution'):
    """CSV orchestration, exercised by offline tests in disposable directories.

    No CLI route enables this while provider execution is prohibited. There is
    deliberately no CLI fake-response mode, provider switch or approval system.
    """
    if os.getenv('EVAL_MODE') != '1':
        raise EvaluationError('Evaluation runner requires EVAL_MODE=1')
    output = Path(output)
    with _lock(assistant.STORE / 'operation.lock'), _lock(output / '.run.lock'):
        identity = assistant._identity(config, manifest_sha)
        expected = _metadata(config, manifest_sha, identity, origin)
        meta_file, csv_file, journal = output / 'run_metadata.json', output / 'records.csv', output / 'attempts.jsonl'
        if resume:
            saved = json.loads(meta_file.read_text())
            if any(saved.get(k) != v for k, v in expected.items()):
                raise EvaluationError('Resume identity changed; existing results were preserved')
            rows = _read_rows(csv_file, data, config)
        else:
            if any(p.exists() for p in (meta_file, csv_file, journal, output / 'retrieval')):
                raise EvaluationError('Existing evaluation artifacts require --resume; nothing was overwritten')
            _write_json(meta_file, {**expected, 'run_id': uuid4().hex, 'created_at': datetime.now(timezone.utc).isoformat()})
            with csv_file.open('x', newline='') as handle:
                csv.writer(handle, lineterminator='\n').writerow(COLUMNS)
                handle.flush()
                os.fsync(handle.fileno())
            rows = {}
        started = _started_rows(journal)
        selected = data['cases'] if limit is None else data['cases'][:limit]
        added = 0
        with csv_file.open('a', newline='') as handle:
            writer = csv.DictWriter(handle, fieldnames=COLUMNS, lineterminator='\n')
            for case in selected:
                modes = [m for m in 'ABC' if (case['case_id'], m) not in rows]
                if not modes:
                    continue
                # Freeze/restore candidate chunks before any mode can dispatch.
                hits, retrieval_error = _case_evidence(case, config, identity, output)
                assistant._install_retrieval(case['query'], case['fixtures'], config, identity, hits)
                for mode in modes:
                    key = case['case_id'], mode
                    if key in started:
                        response = _error_result('Interrupted row; provider completion unknown; not automatically replayed.', hits)
                    elif retrieval_error:
                        response = _error_result(retrieval_error, hits)
                    else:
                        _journal(journal, *key, 'row_started')
                        try:
                            response = assistant.ask(mode, case['query'], case['fixtures'])
                            if not response['answer'].strip() and not response['error']:
                                response = _error_result('Assistant returned an empty answer without an error.', hits)
                        except Exception as exc:
                            response = _error_result(assistant._error_text(exc), hits)
                    try:
                        row = _record(case, mode, response, config)
                    except Exception as exc:
                        row = _record(case, mode, _error_result(assistant._error_text(exc), hits), config)
                    writer.writerow({k: _cell(row[k]) for k in COLUMNS})
                    handle.flush()
                    os.fsync(handle.fileno())
                    _journal(journal, *key, 'row_recorded')
                    rows[key] = row
                    added += 1
        return {'records': len(rows), 'added': added, 'origin': origin}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    selection = parser.add_mutually_exclusive_group()
    selection.add_argument('--limit', type=int, help='First N cases, each in A/B/C; with --resume this is a cumulative prefix')
    selection.add_argument('--all', action='store_true')
    parser.add_argument('--resume', action='store_true')
    operation = parser.add_mutually_exclusive_group()
    operation.add_argument('--plan', action='store_true', help='Read-only request counts; no index/model/provider calls')
    operation.add_argument('--prepare-only', action='store_true', help='Build a fresh local index using cached CPU embeddings only')
    args = parser.parse_args(argv)
    if args.limit is not None and args.limit <= 0:
        parser.error('--limit must be positive')
    try:
        data, config, manifest_sha = _inputs()
        if args.plan:
            print(json.dumps(_plan(data, args.limit), indent=2))
        elif args.prepare_only:
            if args.resume:
                raise EvaluationError('--prepare-only cannot replace the index of a resumed run')
            if any((OUTPUT / name).exists() for name in ('records.csv', 'run_metadata.json', 'attempts.jsonl', 'retrieval')):
                raise EvaluationError('Existing evaluation results prevent replacing the index; preserve it for --resume')
            os.environ['HF_HUB_OFFLINE'] = '1'
            os.environ['TRANSFORMERS_OFFLINE'] = '1'
            with _lock(assistant.STORE / 'operation.lock'):
                report = prepare_store(data, config, assistant.STORE, progress=lambda line: print(line, flush=True))
            print(json.dumps(report, indent=2))
        else:
            raise EvaluationError('Provider evaluation remains disabled by project scope. Use --plan or --prepare-only; no result rows were written.')
    except Exception as exc:
        parser.exit(1, assistant._error_text(exc) + '\n')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
