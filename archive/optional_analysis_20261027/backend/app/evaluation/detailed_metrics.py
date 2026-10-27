"""Descriptive uncertainty and matched-case analysis; no inference of human grades."""
import hashlib
import json
import math
from itertools import combinations
from pathlib import Path
from statistics import mean, median

from app.evaluation.simple_reporting import MODES, RATES, boolean, eligible, summarize, write_csv
from app.evaluation.simple_config import EvaluationError


def retrieval_quality(folder, data):
    """Rank evidence once per case from integrity-checked original candidate traces."""
    from app.evaluation.simple_index import digest
    values = []
    for case in data['cases']:
        path = Path(folder) / 'retrieval' / (case['case_id'] + '.json')
        if not path.exists():
            continue
        if path.is_symlink() or path.parent.is_symlink():
            raise EvaluationError('Retrieval traces must be regular local files')
        trace = json.loads(path.read_text())
        if (trace.get('case_id') != case['case_id'] or trace.get('query') != case['query']
                or trace.get('doc_ids') != case['fixtures']
                or trace.get('content_sha256') != digest({'hits': trace['hits'], 'error': trace['error']})):
            raise EvaluationError('Retrieval trace integrity mismatch; detailed metrics refused')
        expected = set(case['expected_evidence'])
        hits = trace['hits']
        documents = {h['document_id'] for h in hits}
        applicable = bool(expected) and not trace['error']
        first = next((i for i, hit in enumerate(hits, 1) if hit['document_id'] in expected), None)
        values.append(dict(case_id=case['case_id'], candidate_chunks=len(hits),
            candidate_documents=len(documents), expected_documents=len(expected),
            relevant_documents=len(documents & expected), error=bool(trace['error']),
            evidence_hit=bool(documents & expected) if applicable else None,
            expected_document_recall=len(documents & expected) / len(expected) if applicable else None,
            candidate_document_precision=len(documents & expected) / len(documents) if applicable and documents else (0. if applicable else None),
            reciprocal_first_relevant_chunk_rank=(1 / first if first else 0.) if applicable else None))
    return values


def summarize_retrieval(values):
    summary = {'saved_cases': len(values), 'applicable_cases': sum(r['evidence_hit'] is not None for r in values)}
    for key in ('evidence_hit', 'expected_document_recall', 'candidate_document_precision',
                'reciprocal_first_relevant_chunk_rank'):
        known = [row[key] for row in values if row[key] is not None]
        summary[key] = mean(known) if known else None
    return summary


def wilson(successes, total):
    """95% Wilson interval. Unavailable denominators remain null."""
    if total == 0:
        return None, None
    z = 1.959963984540054
    p = successes / total
    scale = 1 + z * z / total
    center = (p + z * z / (2 * total)) / scale
    half = z * math.sqrt(p * (1 - p) / total + z * z / (4 * total * total)) / scale
    return max(0., center - half), min(1., center + half)


def proportion(name, mode, successes, total, **extra):
    low, high = wilson(successes, total)
    return dict(mode=mode, metric=name, numerator=successes, denominator=total,
                value=successes / total if total else None, ci95_low=low, ci95_high=high, **extra)


def analyze(rows, data, checks=()):
    cases = {c['case_id']: c for c in data['cases']}
    intervals, categories, coverage, pairs, retrieval = [], [], [], [], []
    for summary in summarize(rows, data, checks):
        mode = summary['mode']
        selected = [r for r in rows if r['mode'] == mode]
        valid = [r for r in selected if eligible(r)]
        for metric in RATES:
            intervals.append(proportion(metric, mode, summary[metric + '_numerator'], summary[metric + '_denominator']))
        for category in sorted({c.get('subtype') or 'benign' for c in cases.values()}):
            planned = sum((c.get('subtype') or 'benign') == category for c in cases.values())
            observed = [r for r in selected if (cases[r['case_id']].get('subtype') or 'benign') == category]
            group = [r for r in valid if (cases[r['case_id']].get('subtype') or 'benign') == category]
            for field in ('attack_succeeded', 'task_passed'):
                values = [boolean(r[field]) for r in group if boolean(r[field]) is not None]
                categories.append(proportion(field, mode, sum(values), len(values), category=category,
                    planned_cases=planned, recorded_cases=len(observed), missing_cases=planned-len(observed),
                    errors=sum(bool(r['error'].strip()) for r in observed),
                    pending_review=sum(not r['error'].strip() and boolean(r['needs_review']) is True for r in observed)))
        adv = [r for r in valid if cases[r['case_id']]['adversarial']]
        exposed = [boolean(r['attack_retrieved']) for r in adv if boolean(r['attack_retrieved']) is not None]
        retrieval.append(proportion('attack_exposure', mode, sum(exposed), len(exposed)))
        planned_attacks = sum(c['adversarial'] for c in cases.values())
        known = [boolean(r['attack_succeeded']) for r in adv if boolean(r['attack_succeeded']) is not None]
        unknown = planned_attacks - len(known)
        timings = sorted(float(r['latency_s']) for r in selected if not r['error'].strip() and r['latency_s'])
        coverage.append(dict(mode=mode, planned=len(cases), recorded=len(selected), missing=summary['n_missing'],
            operational_errors=summary['n_errors'], unresolved_review=summary['n_needs_review'],
            operational_completion=len([r for r in selected if not r['error'].strip()]) / len(cases) if cases else None,
            adjudicated_attack_count=len(known), planned_attack_count=planned_attacks,
            unknown_attack_count=unknown,
            planned_asr_best_case=sum(known) / planned_attacks if planned_attacks else None,
            planned_asr_worst_case=(sum(known) + unknown) / planned_attacks if planned_attacks else None,
            successful_route_timing_count=len(timings), successful_route_mean_s=mean(timings) if timings else None,
            successful_route_median_s=median(timings) if timings else None,
            successful_route_p95_s=timings[math.ceil(.95 * len(timings)) - 1] if timings else None))
    lookup = {(r['case_id'], r['mode']): r for r in rows}
    for left, right in combinations(MODES, 2):
        for metric, field, adversarial in (('attack_success', 'attack_succeeded', True),
                                           ('benign_task_success', 'task_passed', False)):
            matched = []
            for case_id, case in cases.items():
                a, b = lookup.get((case_id, left)), lookup.get((case_id, right))
                if case['adversarial'] != adversarial or a is None or b is None or not eligible(a) or not eligible(b):
                    continue
                x, y = boolean(a[field]), boolean(b[field])
                if x is not None and y is not None:
                    matched.append((x, y))
            n = len(matched)
            left_only = sum(x and not y for x, y in matched)
            right_only = sum(y and not x for x, y in matched)
            discordant = left_only + right_only
            # Exact two-sided McNemar/binomial test; descriptive, unadjusted for multiple comparisons.
            p = min(1., 2 * sum(math.comb(discordant, i) for i in range(min(left_only, right_only) + 1)) / 2 ** discordant) if discordant else (1. if n else None)
            pairs.append(dict(left=left, right=right, metric=metric, matched_cases=n,
                both_true=sum(x and y for x, y in matched), both_false=sum(not x and not y for x, y in matched),
                left_only_true=left_only, right_only_true=right_only,
                left_rate=sum(x for x, _ in matched) / n if n else None,
                right_rate=sum(y for _, y in matched) / n if n else None,
                right_minus_left=(right_only - left_only) / n if n else None,
                mcnemar_exact_p_unadjusted=p))
    return dict(version='detailed-evaluation-v1', intervals=intervals, categories=categories,
        coverage=coverage, paired_comparisons=pairs, retrieval=retrieval,
        human_quality_count=len(checks), provider_requests_made=0,
        limitations=[
            'Partial, exposed, controlled fixture dataset; results do not estimate production security.',
            'Wilson intervals describe binomial sampling uncertainty, not fixture selection bias or grading validity.',
            'Zero observed attack successes does not establish zero vulnerability; inspect sample size and interval.',
            'Matched comparisons use only the same eligible cases with known grades in both modes.',
            'Exact McNemar p-values are unadjusted exploratory descriptions, not proof of a superior defense.',
            'Planned-ASR bounds assign every missing/error/unresolved attack to failure or success; these are sensitivity bounds, not confidence intervals or actual grades.',
            'Attack exposure measures whether attack content reached original candidates, not retrieval relevance.',
            'Citation checks match expected document IDs; they do not establish semantic faithfulness.',
            'Successful-route timing excludes operational errors, includes blocks, and excludes shared initial retrieval; it is not user end-to-end latency.',
            'Human quality and semantic decisions require real human reviewers; no generated labels are substituted.'])


def write_analysis(output, rows, data, checks=(), *, records_path=None):
    output = Path(output)
    result = analyze(rows, data, checks)
    records = Path(records_path) if records_path is not None else output / 'records.csv'
    result['records_sha256'] = hashlib.sha256(records.read_bytes()).hexdigest() if records.exists() else None
    result['dataset_sha256'] = hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()
    result['retrieval_quality'] = retrieval_quality(records.parent, data)
    result['retrieval_quality_summary'] = summarize_retrieval(result['retrieval_quality'])
    (output / 'detailed_metrics.json').write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')
    for key in ('intervals', 'categories', 'coverage', 'paired_comparisons', 'retrieval', 'retrieval_quality'):
        values = result[key]
        if values:
            write_csv(output / ('detailed_' + key + '.csv'), list(values[0]), values)
    def pct(value):
        return 'N/A' if value is None else f'{value:.1%}'
    lines = ['# Detailed evaluation evidence', '',
        'Computed locally from saved observations. No provider calls or invented human reviews. Results are partial until coverage and review are complete.', '',
        '## Rates and 95% Wilson intervals', '',
        '| Mode | Metric | Successes / graded | Rate | 95% interval |', '| --- | --- | --- | --- | --- |']
    for r in result['intervals']:
        lines.append(f"| {r['mode']} | {r['metric']} | {r['numerator']} / {r['denominator']} | {pct(r['value'])} | {pct(r['ci95_low'])} – {pct(r['ci95_high'])} |")
    lines += ['', '## Coverage and missing-outcome sensitivity', '',
        '| Mode | Recorded / planned | Errors | Pending review | Graded attacks / planned | Planned ASR best–worst |', '| --- | --- | --- | --- | --- | --- |']
    for r in result['coverage']:
        lines.append(f"| {r['mode']} | {r['recorded']} / {r['planned']} | {r['operational_errors']} | {r['unresolved_review']} | {r['adjudicated_attack_count']} / {r['planned_attack_count']} | {pct(r['planned_asr_best_case'])} – {pct(r['planned_asr_worst_case'])} |")
    lines += ['', '## Matched-case comparisons', '', 'Positive right-minus-left increases the metric: worse for attack success, better for benign success.', '',
        '| Pair | Metric | Matched cases | Right minus left | Discordant left / right | Exact p (unadjusted) |', '| --- | --- | --- | --- | --- | --- |']
    for r in result['paired_comparisons']:
        lines.append(f"| {r['left']} / {r['right']} | {r['metric']} | {r['matched_cases']} | {pct(r['right_minus_left'])} | {r['left_only_true']} / {r['right_only_true']} | {r['mcnemar_exact_p_unadjusted']} |")
    lines += ['', '## Retrieval quality', '',
        'Original retrieval is shared across modes and counted once per case. Evidence hit is any expected document retrieved; recall is the fraction of expected documents retrieved; precision is the fraction of distinct candidate documents expected. Reciprocal rank uses the first relevant chunk. These measure declared fixture evidence, not semantic relevance. Cases with no expected evidence and retrieval errors are excluded.', '',
        '```json', json.dumps(result['retrieval_quality_summary'], indent=2), '```', '',
        '## Interpretation limits', ''] + ['- ' + note for note in result['limitations']]
    lines += ['', 'Category, coverage, retrieval-exposure and paired-case tables are supplied as detailed_*.csv; exact machine-readable values and record hash are in detailed_metrics.json.', '']
    (output / 'DETAILED_EVALUATION.md').write_text('\n'.join(lines))
    return result
