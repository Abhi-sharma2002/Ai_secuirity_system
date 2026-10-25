"""Compute local v3 metrics and charts; missing records stay explicitly unavailable."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'backend'))
from app.evaluation.simple_reporting import make_report
from app.evaluation.simple_runner import _error_text


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--records', type=Path, default=ROOT / 'results/records.csv')
    parser.add_argument('--output', type=Path, default=ROOT / 'results')
    args = parser.parse_args(argv)
    try:
        print(json.dumps(make_report(args.records, args.output), indent=2))
    except Exception as exc:
        parser.exit(1, _error_text(exc) + '\n')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
