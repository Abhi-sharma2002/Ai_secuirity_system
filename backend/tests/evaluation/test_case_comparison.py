"""A shared case must preserve mode-specific observations and unavailable grades."""
from copy import deepcopy
from app.evaluation.case_comparison import compare_cases
from backend.tests.evaluation.test_simple_reporting import DATA, ATTACKS, row


def test_same_case_keeps_errors_missing_modes_and_distinct_answers():
    case = ATTACKS[0]
    rows = [row(case, 'A', answer='A actual observation', attack_succeeded='true'),
            row(case, 'C', answer='', error='provider_content_filter', attack_succeeded='false', task_passed='false')]
    before = deepcopy(rows)
    compared = next(c for c in compare_cases(rows, DATA) if c['case_id'] == case['case_id'])
    assert compared['fixtures'] == case['fixtures']
    assert compared['modes']['A']['attack_succeeded'] is True
    assert compared['modes']['A']['answer'] == 'A actual observation'
    assert compared['modes']['B']['state'] == 'Not run'
    assert compared['modes']['C']['state'] == 'Operational error'
    assert compared['modes']['C']['attack_succeeded'] is None
    assert compared['modes']['C']['task_passed'] is None
    assert rows == before


def test_screening_block_is_distinct_from_error_and_pending_human_judgment():
    case = ATTACKS[0]
    rows = [row(case, 'B', needs_review='true', attack_succeeded='true'),
            row(case, 'C', blocked='true', question_flagged='true', task_passed='false')]
    compared = next(c for c in compare_cases(rows, DATA) if c['case_id'] == case['case_id'])
    assert compared['modes']['B']['state'] == 'Needs human review'
    assert compared['modes']['B']['attack_succeeded'] is None
    assert compared['modes']['C']['state'] == 'Blocked'
    assert compared['modes']['C']['question_flagged'] is True
