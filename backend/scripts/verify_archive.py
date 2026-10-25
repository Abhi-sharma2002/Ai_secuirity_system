"""Verify the historical files preserved by cleanup, without importing retired code."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def main():
    entries = json.loads((ROOT / 'archive/path_map.json').read_text())
    for entry in entries:
        path = ROOT / entry['archived']
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != entry['sha256']:
            raise SystemExit('Archived file missing or changed: ' + entry['archived'])
    aliases = ['docs/history', 'backend/app/legacy', 'backend/legacy_llm',
               'backend/historical_tests', 'backend/scripts/history']
    for name in aliases:
        path = ROOT / name
        if not path.is_symlink() or path.resolve() != ROOT / 'archive' / name:
            raise SystemExit('Historical compatibility alias is missing: ' + name)
    print(json.dumps({'archived_files_verified': len(entries), 'compatibility_aliases_verified': len(aliases)}, indent=2))


if __name__ == '__main__':
    main()
