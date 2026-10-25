"""Write/check the v3 report and metrics explainer against actual CSV data."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'backend'))
from app.evaluation.simple_documents import write_documents
from app.evaluation.simple_runner import _error_text


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--results', type=Path, default=ROOT / 'results')
    parser.add_argument('--output', type=Path, default=ROOT / 'docs')
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args(argv)
    try:
        print(json.dumps(write_documents(args.results, args.output, args.check), indent=2))
    except Exception as exc:
        parser.exit(1, _error_text(exc) + '\n')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
