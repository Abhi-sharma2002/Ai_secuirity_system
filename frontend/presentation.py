"""Display-only formatting; never creates judgments or replaces missing metrics."""
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
