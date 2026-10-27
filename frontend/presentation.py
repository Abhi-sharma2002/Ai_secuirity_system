"""Display-only formatting; never creates judgments or replaces missing metrics."""
def answer_preview(value):
    """Copy a UI view, masking credentials, emails, canaries and unverified cards."""
    from frontend.redaction import mask_text, SECRET_FIELD
    if isinstance(value, str):
        return mask_text(value)
    if isinstance(value, list):
        return [answer_preview(item) for item in value]
    if isinstance(value, dict):
        return {answer_preview(k): ('[credential hidden]' if isinstance(k, str) and SECRET_FIELD.fullmatch(k)
                                    else answer_preview(v)) for k, v in value.items()}
    return value


def answer_view(value):
    """Only the answer, status and citation locations belong in the Ask view."""
    preview = answer_preview(value)
    result = {key: preview[key] for key in ('mode', 'status', 'answer', 'error', 'latency_ms', 'reservation_units')
              if key in preview}
    result['references'] = [
        {key: ref[key] for key in ('filename', 'page', 'section', 'partial_text') if key in ref}
        for ref in preview.get('references', [])
    ]
    return result


def comparison_view(value):
    """Interactive downloads contain answers/citation locations, never audit text."""
    preview = answer_preview(value)
    return {**{key: preview[key] for key in ('status', 'error') if key in preview},
            'results': {mode: answer_view(response) for mode, response in preview.get('results', {}).items()
                        if response is not None}}


def metric_rows(summary):
    rows = []
    for mode, values in summary.get('by_mode', {}).items():
        row = {'Configuration': mode}
        for label, key in [('Attack success rate', 'attack_success'), ('Benign task success', 'benign_task_success'),
                           ('Benign screening flags', 'benign_flags'), ('Benign blocks', 'benign_blocks')]:
            metric = values.get(key, {})
            n, rate = metric.get('denominator', 0), metric.get('rate')
            row[label] = 'Not evaluable (n=0)' if not n or rate is None else f'{rate:.1%} ({metric.get("successes", "?")}/{n})'
        quality = values.get('quality', {})
        row['Quality / 4'] = ('Unreviewed' if quality.get('mean') is None else f'{quality["mean"]:.2f} (n={quality.get("graded", 0)})')
        latency = values.get('latency_ms', {})
        row['Mean latency (s)'] = ('Unknown' if latency.get('mean') is None else f'{latency["mean"]/1000:.2f} (n={latency.get("observed", "?")})')
        row['Operational errors'] = values.get('operational_errors', 0)
        rows.append(row)
    return rows


def evaluation_metric_rows(summary, definitions):
    modes = {row['mode']: row for row in summary}
    result = []
    for definition in definitions:
        key, kind = definition['key'], definition['kind']
        row = {'Metric': definition['metric']}
        for mode in 'ABC':
            values = modes.get(mode, {})
            value = values.get(key)
            if value is None:
                text = 'N/A (C only)' if key in {'false_positive_rate', 'answer_chunk_removed_rate', 'false_positive_total', 'pdf_false_positive_rate'} and mode != 'C' else 'N/A'
            elif kind == 'rate':
                text = f"{value:.1%} ({values[key+'_numerator']}/{values[key+'_denominator']})"
            elif kind == 'seconds':
                text = f"{value:.3f} s (n={values['n_latency']})"
            elif kind == 'quality':
                text = f"{value:.2f}/4 (n={values['n_quality']})"
            else:
                text = f"{value:.1%} (n={values['n_agreement']})"
            row[mode] = text
        result.append(row)
    return result


def page_label(page):
    return f'Page {page}' if isinstance(page, int) and page > 0 else 'Page not established'


def expiry_label(value):
    from datetime import datetime
    from zoneinfo import ZoneInfo
    try:
        parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
        if parsed.tzinfo is None:
            return 'Unknown expiry timezone'
        return parsed.astimezone(ZoneInfo('Asia/Kolkata')).strftime('%d %b %Y, %I:%M:%S %p IST')
    except (TypeError, ValueError, AttributeError):
        return 'Unknown expiry'
