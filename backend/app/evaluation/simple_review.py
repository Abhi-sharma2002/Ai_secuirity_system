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
    sample = sample_rows(rows)
    checks = [{**{k: r[k] for k in ('case_id', 'mode', 'query', 'expected_behavior', 'answer', 'sources')},
               'record_sha256': row_digest(r), 'automated_attack_succeeded': r['attack_succeeded'],
               'automated_task_passed': r['task_passed'], 'attack_correct': '', 'task_correct': '',
               'quality_0_4': '', 'reviewer': ''} for r in sample]
    path = output / 'spot_check.csv'
    if path.exists():
        existing = list(csv.DictReader(path.open(newline='')))
        current = {(r['case_id'], r['mode']): row_digest(r) for r in rows if eligible(r)}
        merged = {(r['case_id'], r['mode']): r for r in checks}
        for check in existing:
            key = check['case_id'], check['mode']
            if current.get(key) == check['record_sha256']:
                # Preserve actual earlier judgments when new rows change the sample.
                if key in merged or any(check.get(k) for k in ('reviewer', 'quality_0_4', 'task_correct', 'attack_correct')):
                    merged[key] = check
        checks = list(merged.values())
        if existing != checks and existing:
            history = output / '.review_history' / uuid4().hex
            history.mkdir(parents=True)
            shutil.copy2(path, history / 'spot_check.before.csv')
    write_csv(path, SPOT_COLUMNS, checks)
    n_sample = len(checks)
    checked = read_spot_checks(output / 'spot_check.csv', rows)
    status = {'status': 'no_records' if not rows else 'needs_review' if pending else 'sample_ready' if checks else 'no_eligible_answers',
              'n_records': len(rows), 'n_pending_review': len(pending), 'n_sample_rows': n_sample,
              'n_human_checked': len(checked), 'agreement': sum(c['agreed'] for c in checked) / len(checked) if checked else None,
              'seed': 42, 'provider_requests_made': 0}
    (output / 'spot_check_status.json').write_text(json.dumps(status, indent=2) + '\n')
    return status


def apply_decisions(records, decisions, *, allow_partial=False):
    from scripts.run_eval import COLUMNS, _lock
    records, decisions = Path(records), Path(decisions)
    with _lock(records.parent / '.run.lock'):
        rows = read_records(records)
        pending = {(r['case_id'], r['mode']): r for r in rows if not r['error'].strip() and (allow_partial or boolean(r['needs_review']) is True)}
        if not pending:
            raise EvaluationError('There are no recorded rows awaiting human decisions')
        with decisions.open(newline='') as handle:
            reader = csv.DictReader(handle, strict=True)
            if reader.fieldnames != REVIEW_COLUMNS:
                raise EvaluationError('Human decision form has a different header')
            forms = list(reader)
        supplied = {(f['case_id'], f['mode']): f for f in forms}
        if len(supplied) != len(forms) or not supplied or (not supplied.keys() <= pending.keys() if allow_partial else supplied.keys() != pending.keys()):
            raise EvaluationError('Decisions must cover every pending row exactly once')
        cases = {c['case_id']: c for c in manifest()['cases']}
        updates = {}
        for key in supplied:
            row = pending[key]
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


def submit_quality(records, output, *, case_id, mode, record_sha256, reviewer,
                   quality_0_4, task_correct, attack_correct):
    """Persist an explicitly entered human review against one exact saved answer."""
    from scripts.run_eval import _lock
    records, output = Path(records), Path(output)
    with _lock(records.parent / '.run.lock'):
        rows = read_records(records)
        row = next((r for r in rows if (r['case_id'], r['mode']) == (case_id, mode)), None)
        if row is None or not eligible(row) or row_digest(row) != record_sha256:
            raise EvaluationError('Answer is missing, changed, errored or awaiting a scoring decision; refresh first')
        if not reviewer.strip() or type(quality_0_4) is not int or quality_0_4 not in range(5) or type(task_correct) is not bool:
            raise EvaluationError('Enter your name, quality from 0 to 4 and an explicit task-grade judgment')
        applicable = boolean(row['attack_succeeded']) is not None
        if (applicable and type(attack_correct) is not bool) or (not applicable and attack_correct is not None):
            raise EvaluationError('Attack-grade agreement is required only for attack cases')
        path = output / 'spot_check.csv'
        existing = list(csv.DictReader(path.open(newline=''))) if path.exists() else []
        check = {**{k: row[k] for k in ('case_id', 'mode', 'query', 'expected_behavior', 'answer', 'sources')},
                 'record_sha256': record_sha256, 'automated_attack_succeeded': row['attack_succeeded'],
                 'automated_task_passed': row['task_passed'], 'task_correct': str(task_correct).lower(),
                 'attack_correct': '' if attack_correct is None else str(attack_correct).lower(),
                 'quality_0_4': str(quality_0_4), 'reviewer': reviewer.strip()}
        updated = [r for r in existing if (r['case_id'], r['mode']) != (case_id, mode)] + [check]
        staging = output / f'.quality-{uuid4().hex}.csv'
        try:
            write_csv(staging, SPOT_COLUMNS, updated)
            read_spot_checks(staging, rows)
            if path.exists():
                history = output / '.review_history' / uuid4().hex
                history.mkdir(parents=True)
                shutil.copy2(path, history / 'spot_check.before.csv')
            staging.replace(path)
        finally:
            staging.unlink(missing_ok=True)
        return {'saved': True, 'case_id': case_id, 'mode': mode, 'provider_requests_made': 0}


def submit_judgment(records, output, *, case_id, mode, record_sha256, reviewer,
                    rationale, task_passed, attack_succeeded, answer_chunk_removed=None):
    """Apply one explicit human decision, preserving the previous raw CSV."""
    records, output = Path(records), Path(output)
    rows = read_records(records)
    row = next((r for r in rows if (r['case_id'], r['mode']) == (case_id, mode)), None)
    if row is None or row['error'].strip() or row_digest(row) != record_sha256:
        raise EvaluationError('The recorded answer changed or is an operational error; refresh first')
    case = next(c for c in manifest()['cases'] if c['case_id'] == case_id)
    form = {k: row.get(k, '') for k in REVIEW_COLUMNS}
    def cell(value):
        if value is None:
            return ''
        if type(value) is not bool:
            raise EvaluationError('Explicit boolean judgments are required')
        return str(value).lower()
    form.update(record_sha256=record_sha256, reviewer=reviewer, rationale=rationale,
                expected_evidence=json.dumps(case['expected_evidence']), supporting_quotes=json.dumps(case['supporting_quotes']),
                task_passed=cell(task_passed), attack_succeeded=cell(attack_succeeded),
                answer_chunk_removed=cell(answer_chunk_removed))
    staging = output / f'.decision-{uuid4().hex}.csv'
    try:
        write_csv(staging, REVIEW_COLUMNS, [form])
        result = apply_decisions(records, staging, allow_partial=True)
    finally:
        staging.unlink(missing_ok=True)
    # Old review forms retain their history; refreshed forms bind the new row digest.
    pending_form = output / 'review_decisions.csv'
    if pending_form.exists():
        history = output / '.review_history' / uuid4().hex
        history.mkdir(parents=True)
        shutil.move(str(pending_form), str(history / 'review_decisions.before.csv'))
    prepare(records, output)
    return result
