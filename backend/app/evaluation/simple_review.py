"""Prepare human forms and apply explicit judgments; never infer human labels."""
import csv
import hashlib
import json
from pathlib import Path
import shutil
from uuid import uuid4

from app.evaluation.simple_config import ROOT, EvaluationError
from app.evaluation.simple_reporting import (boolean, eligible, manifest, read_records,
                                           read_spot_checks, row_digest, sample_rows, write_csv)

REVIEW_COLUMNS = ['case_id', 'mode', 'record_sha256', 'query', 'expected_behavior',
                  'expected_evidence', 'supporting_quotes', 'answer', 'sources',
                  'retrieved_chunk_ids', 'kept_chunk_ids', 'removed_chunk_ids',
                  'attack_succeeded', 'task_passed', 'answer_chunk_removed', 'reviewer', 'rationale']
SPOT_COLUMNS = ['case_id', 'mode', 'record_sha256', 'query', 'expected_behavior', 'answer',
                'sources', 'automated_attack_succeeded', 'automated_task_passed',
                'attack_correct', 'task_correct', 'quality_0_4', 'reviewer']


def _form(path, columns, rows):
    if path.exists():
        with path.open(newline='') as handle:
            reader = csv.DictReader(handle)
            if reader.fieldnames != columns:
                raise EvaluationError('Existing review form has a different header; preserved')
            existing = list(reader)
        if existing:
            expected = {(r['case_id'], r['mode']): r['record_sha256'] for r in rows}
            if (len(existing) != len(expected)
                    or len({(r['case_id'], r['mode']) for r in existing}) != len(existing)
                    or any(expected.get((r['case_id'], r['mode'])) != r['record_sha256'] for r in existing)):
                raise EvaluationError('Existing review form is stale; preserve it separately before preparing another')
            return len(existing)
    write_csv(path, columns, rows)
    return len(rows)


def prepare(records, output):
    records, output = Path(records), Path(output)
    rows = read_records(records)
    data = manifest()
    cases = {c['case_id']: c for c in data['cases']}
    pending = [r for r in rows if not r['error'].strip() and boolean(r['needs_review']) is True]
    forms = []
    for row in pending:
        case = cases[row['case_id']]
        forms.append({**{k: row[k] for k in ('case_id', 'mode', 'query', 'expected_behavior', 'answer',
                                             'sources', 'retrieved_chunk_ids', 'kept_chunk_ids', 'removed_chunk_ids')},
                      'record_sha256': row_digest(row), 'expected_evidence': json.dumps(case['expected_evidence']),
                      'supporting_quotes': json.dumps(case['supporting_quotes']),
                      'attack_succeeded': '', 'task_passed': '', 'answer_chunk_removed': '', 'reviewer': '', 'rationale': ''})
    output.mkdir(parents=True, exist_ok=True)
    # Preserve an applied form when nothing remains to review.
    if pending or not (output / 'review_decisions.csv').exists():
        _form(output / 'review_decisions.csv', REVIEW_COLUMNS, forms)
    complete = len(rows) == len(data['cases']) * 3
    sample = sample_rows(rows) if complete and not pending else []
    if any(sum(r['mode'] == mode for r in sample) != 10 for mode in 'ABC'):
        sample = []
    checks = [{**{k: r[k] for k in ('case_id', 'mode', 'query', 'expected_behavior', 'answer', 'sources')},
               'record_sha256': row_digest(r), 'automated_attack_succeeded': r['attack_succeeded'],
               'automated_task_passed': r['task_passed'], 'attack_correct': '', 'task_correct': '',
               'quality_0_4': '', 'reviewer': ''} for r in sample]
    n_sample = _form(output / 'spot_check.csv', SPOT_COLUMNS, checks)
    checked = read_spot_checks(output / 'spot_check.csv', rows)
    status = {'status': 'no_records' if not rows else 'needs_review' if pending else 'sample_ready' if sample else 'waiting_for_complete_comparison',
              'n_records': len(rows), 'n_pending_review': len(pending), 'n_sample_rows': n_sample,
              'n_human_checked': len(checked), 'agreement': sum(c['agreed'] for c in checked) / len(checked) if checked else None,
              'seed': 42, 'provider_requests_made': 0}
    (output / 'spot_check_status.json').write_text(json.dumps(status, indent=2) + '\n')
    return status


def apply_decisions(records, decisions):
    from scripts.run_eval import COLUMNS, _lock
    records, decisions = Path(records), Path(decisions)
    with _lock(records.parent / '.run.lock'):
        rows = read_records(records)
        pending = {(r['case_id'], r['mode']): r for r in rows if not r['error'].strip() and boolean(r['needs_review']) is True}
        if not pending:
            raise EvaluationError('There are no recorded rows awaiting human decisions')
        with decisions.open(newline='') as handle:
            reader = csv.DictReader(handle, strict=True)
            if reader.fieldnames != REVIEW_COLUMNS:
                raise EvaluationError('Human decision form has a different header')
            forms = list(reader)
        supplied = {(f['case_id'], f['mode']): f for f in forms}
        if len(supplied) != len(forms) or supplied.keys() != pending.keys():
            raise EvaluationError('Decisions must cover every pending row exactly once')
        cases = {c['case_id']: c for c in manifest()['cases']}
        updates = {}
        for key, row in pending.items():
            form, case = supplied[key], cases[key[0]]
            if form['record_sha256'] != row_digest(row):
                raise EvaluationError('Human decision belongs to a changed record')
            if not form['reviewer'].strip() or not form['rationale'].strip():
                raise EvaluationError('Every decision requires a human reviewer and rationale')
            attack, task, removed = (boolean(form[k]) for k in ('attack_succeeded', 'task_passed', 'answer_chunk_removed'))
            if task is None or (case['adversarial'] and attack is None) or (not case['adversarial'] and attack is not None):
                raise EvaluationError('Explicit task/attack decisions are required where applicable')
            removal_needed = not case['adversarial'] and row['mode'] == 'C' and row['answer_chunk_removed'] == ''
            if removal_needed and removed is None:
                raise EvaluationError('Semantic answer-evidence removal requires an explicit human decision')
            if not removal_needed and removed is not None:
                raise EvaluationError('This row does not require a removal override')
            updates[key] = {**row, 'attack_succeeded': form['attack_succeeded'], 'task_passed': form['task_passed'],
                            'answer_chunk_removed': form['answer_chunk_removed'] if removal_needed else row['answer_chunk_removed'],
                            'needs_review': 'false'}
        backup = ROOT / 'archive/evaluation_reviews' / uuid4().hex
        backup.mkdir(parents=True)
        shutil.copy2(records, backup / 'records.before.csv')
        shutil.copy2(decisions, backup / 'human_decisions.csv')
        staged = records.parent / f'records-reviewed-{uuid4().hex}.csv'
        write_csv(staged, COLUMNS, [updates.get((r['case_id'], r['mode']), r) for r in rows])
        staged.replace(records)
        audit = {'n_applied': len(updates), 'before_sha256': hashlib.sha256((backup / 'records.before.csv').read_bytes()).hexdigest(),
                 'after_sha256': hashlib.sha256(records.read_bytes()).hexdigest(), 'provider_requests_made': 0}
        (backup / 'audit.json').write_text(json.dumps(audit, indent=2) + '\n')
        return audit
