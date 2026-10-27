"""Audit every test case against its documents and saved A/B/C outcomes, offline."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'backend'))
from app.evaluation.case_audit import write_case_audit
from app.evaluation.simple_reporting import read_records, manifest
from app.evaluation.simple_runner import _error_text
from app.evaluation.simple_config import EvaluationError
from scripts.validate_v3 import validate


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--records', type=Path, default=ROOT / 'results/records.csv')
    parser.add_argument('--output', type=Path, default=ROOT / 'results')
    args = parser.parse_args(argv)
    try:
        validation = validate()
        data = manifest()
        rows = read_records(args.records, data)
        metadata = args.records.parent / 'run_metadata.json'
        if metadata.exists() and 'synthetic' in str(json.loads(metadata.read_text()).get('origin', '')).lower() and args.output.resolve() == (ROOT / 'results').resolve():
            raise EvaluationError('Synthetic records cannot generate production case-audit artifacts')
        args.output.mkdir(parents=True, exist_ok=True)
        status = write_case_audit(args.output, args.records, rows, data)
        print(json.dumps({'dataset_validation': validation, 'case_evaluation': status}, indent=2))
    except Exception as exc:
        parser.exit(1, _error_text(exc) + '\n')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
