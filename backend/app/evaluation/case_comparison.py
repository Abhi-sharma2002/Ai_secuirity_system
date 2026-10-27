"""Same-case evidence views derived from saved records; no model execution."""
import json
from app.evaluation.simple_reporting import boolean, eligible

DEFENSES = {
    'A': {'name': 'Grounded baseline', 'pipeline': 'Retrieve → grounded answer with citations',
          'difference': 'Uses the shared grounding, abstention and conflict instructions.'},
    'B': {'name': 'Instruction separation', 'pipeline': 'Retrieve → separate instructions from untrusted data → answer',
          'difference': 'Adds a trust boundary around the question and source content. It does not screen or remove chunks.'},
    'C': {'name': 'Screening and output checks', 'pipeline': 'Retrieve → screen question and chunks → block/filter → B answer → output check',
          'difference': 'Can block the question, remove flagged evidence, or withhold a prohibited output. Screening adds a possible provider call and can lose useful evidence.'},
}


def compare_cases(rows, data):
    lookup = {(r['case_id'], r['mode']): r for r in rows}
    result = []
    for case in data['cases']:
        item = {k: case.get(k) for k in ('case_id', 'query', 'expected_task', 'expected_behavior',
            'expected_evidence', 'supporting_quotes', 'fixtures', 'adversarial', 'channel', 'subtype')}
        item['modes'] = {}
        for mode in 'ABC':
            row = lookup.get((case['case_id'], mode))
            if row is None:
                item['modes'][mode] = {'state': 'Not run', 'answer': None}
                continue
            error = bool(row['error'].strip())
            pending = boolean(row['needs_review']) is True
            state = ('Operational error' if error else 'Needs human review' if pending else
                     'Blocked' if boolean(row['blocked']) is True else 'Answered')
            values = dict(state=state, answer=row['answer'], error=row['error'], latency_s=row['latency_s'])
            for key in ('attack_succeeded', 'task_passed', 'citation_correct'):
                values[key] = boolean(row[key]) if eligible(row) else None
            values['question_flagged'] = boolean(row['question_flagged']) if not error else None
            for key in ('retrieved_chunk_ids', 'kept_chunk_ids', 'removed_chunk_ids', 'sources', 'screen_reasons'):
                values[key] = json.loads(row[key]) if row[key] else ([] if key != 'screen_reasons' else {})
            values['retention_note'] = ''
            if mode in {'A', 'B'} and not values['kept_chunk_ids'] and values['retrieved_chunk_ids']:
                values['kept_chunk_ids'] = list(values['retrieved_chunk_ids'])
                values['retention_note'] = 'Historical retained-ID field was empty. A/B forward original candidates without screening; this view derives that fact from the pipeline, not a saved retained-ID trace.'
            item['modes'][mode] = values
        result.append(item)
    return result
