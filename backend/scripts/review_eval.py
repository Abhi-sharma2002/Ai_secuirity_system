"""Prepare human review forms or import explicit decisions; no provider calls."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'backend'))
from app.evaluation.simple_review import prepare, apply_decisions
from app.evaluation.simple_runner import _error_text


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--records', type=Path, default=ROOT / 'results/records.csv')
    parser.add_argument('--output', type=Path, default=ROOT / 'results')
    actions = parser.add_mutually_exclusive_group(required=True)
    actions.add_argument('--prepare', action='store_true')
    actions.add_argument('--apply', type=Path, metavar='HUMAN_DECISIONS_CSV')
    args = parser.parse_args(argv)
    try:
        status = apply_decisions(args.records, args.apply) if args.apply else prepare(args.records, args.output)
        print(json.dumps(status, indent=2))
    except Exception as exc:
        parser.exit(1, _error_text(exc) + '\n')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
