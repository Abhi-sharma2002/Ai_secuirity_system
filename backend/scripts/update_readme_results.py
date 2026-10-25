"""Update only the README result table from verified CSV observations."""
import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'backend'))
from app.evaluation.simple_documents import _verified, fmt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    _, _, _, summary = _verified(ROOT / 'results')
    path = ROOT / 'README.md'
    original = path.read_text()
    start, end = '<!-- v3-summary:start -->', '<!-- v3-summary:end -->'
    before, body = original.split(start)
    _, after = body.split(end)
    table = ['| Configuration | Recorded | ASR | Benign success | Quality |', '| --- | --- | --- | --- | --- |']
    table.extend(f'| {s["mode"]} | {s["n_recorded"]} | {fmt(s["asr_all"], True)} | {fmt(s["benign_task_success"], True)} | {fmt(s["mean_quality"])} |' for s in summary)
    updated = before + start + '\n' + '\n'.join(table) + '\n' + end + after
    if args.check and updated != original:
        parser.exit(1, 'README result table differs from verified summary\n')
    if not args.check:
        path.write_text(updated)
    print('README result table matches verified summary.')


if __name__ == '__main__':
    main()
