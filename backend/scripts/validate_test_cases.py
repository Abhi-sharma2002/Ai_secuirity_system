"""Run with PYTHONPATH=backend python -m scripts.validate_test_cases."""
import sys
from collections import Counter

from app.evaluation.test_case_loader import load_test_cases, TestCaseValidationError


def main() -> int:
    try:
        cases = load_test_cases()
    except TestCaseValidationError as exc:
        print(f'FAIL: {exc}', file=sys.stderr)
        return 1
    print(f'Total validated test cases: {len(cases)}')
    for field in ('test_family', 'evidence_mode', 'expected_screening_label'):
        print(f'Count by {field}:')
        for label, count in sorted(Counter(case[field] for case in cases).items()):
            print(f'  {label}: {count}')
    print(f'Cases containing attack fixtures: {sum(case["attack_fixture"] is not None for case in cases)}')
    print(f'Benign cases (declared label): {sum(case["expected_screening_label"] == "benign" for case in cases)}')
    print('Source integrity: VERIFIED (manifest hashes, supporting hashes when provided, quotes and fixture sections)')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
