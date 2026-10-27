"""Build, validate or plan the five-case document suite. These commands make no model calls."""
import argparse
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.evaluation.document_suite import DIRECTORY, build, load, snapshot


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build', action='store_true')
    parser.add_argument('--live', action='store_true', help='Requires a separate explicitly approved privacy scope; no scope is created')
    args = parser.parse_args()
    if args.build:
        data = build()
        target = DIRECTORY/'manifest.json'
        if target.exists() and json.loads(target.read_text()) != data:
            parser.error('Existing suite differs; preserve it and create a separately versioned suite')
        DIRECTORY.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(data, indent=2)+'\n')
    if args.live:
        from app.evaluation.document_suite_runner import run
        run()
    value = snapshot()
    print(json.dumps({k: value[k] for k in ('n_documents','n_cases','planned_rows','recorded_rows','max_provider_calls')}, indent=2))
    if not args.live:
        print('Provider requests made: 0. Live execution requires a new, explicit bounded authorization.')


if __name__ == '__main__': main()
