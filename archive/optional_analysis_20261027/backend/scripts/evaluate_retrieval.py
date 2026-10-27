"""Evaluate all frozen cases against the existing CPU index, without generation."""
import hashlib
import argparse
from copy import deepcopy
import json
import os
from pathlib import Path
import sys

# Enforce local cached embeddings before imports; no provider boundary is enabled.
os.environ.update(HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1',
                  LIVE_EVALUATION_ENABLED='false', LIVE_LLM_ENABLED='false')
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'backend'))

from app.evaluation import simple_runner as assistant
from app.evaluation.detailed_metrics import retrieval_quality, summarize_retrieval
from app.evaluation.simple_config import load_config, EvaluationError
from app.storage import registry
from scripts.run_eval import _case_evidence, _lock
from scripts.validate_v3 import validate


def call_count():
    with registry.connect() as db:
        return db.execute('SELECT COUNT(*) FROM calls').fetchone()[0]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--global-corpus', action='store_true',
                        help='Separate diagnostic across all documents; never changes benchmark candidate traces')
    args = parser.parse_args()
    validate()
    data, manifest_sha = assistant._manifest()
    config = load_config()
    identity = assistant._identity(config, manifest_sha)
    output = ROOT / 'results'
    if args.global_corpus:
        output = output / 'global_retrieval'
        data = deepcopy(data)
        all_documents = [f['fixture_id'] for f in data['fixtures']]
        for case in data['cases']:
            case['fixtures'] = list(all_documents)
    output.mkdir(parents=True, exist_ok=True)
    before_calls = call_count()
    records = ROOT / 'results/records.csv'
    before_records = hashlib.sha256(records.read_bytes()).hexdigest() if records.exists() else None
    existing = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in (output / 'retrieval').glob('*.json')}
    with _lock(assistant.STORE / 'operation.lock'), _lock(output / '.run.lock'):
        for number, case in enumerate(data['cases'], 1):
            _, error = _case_evidence(case, config, identity, output)
            if error:
                raise EvaluationError('Local retrieval failed; saved trace retained; no generation or retry performed')
            if number % 10 == 0 or number == len(data['cases']):
                print(f'Checked local retrieval {number}/{len(data["cases"])}', flush=True)
        quality = retrieval_quality(output, data)
        if any(hashlib.sha256(path.read_bytes()).hexdigest() != value for path, value in existing.items()):
            raise EvaluationError('Existing evidence changed during local retrieval evaluation')
        after_records = hashlib.sha256(records.read_bytes()).hexdigest() if records.exists() else None
        if after_records != before_records or call_count() != before_calls:
            raise EvaluationError('Record/accounting invariant changed during local retrieval evaluation')
        status = dict(status='complete_local_retrieval', summary=summarize_retrieval(quality),
            cases=len(data['cases']), documents=len(data['fixtures']), index_identity=identity,
            previous_trace_count=len(existing), previous_traces_preserved=True,
            raw_generation_records_preserved=True, provider_requests_made=0,
            scope='global_corpus_diagnostic' if args.global_corpus else 'case_selected_documents',
            note=('All 45 frozen documents compete. Exact expected document IDs define relevance. Repeated questions and semantically similar fixture copies make those labels non-exhaustive; this is a separate diagnostic, not an A/B/C outcome.' if args.global_corpus else
                  'Only case-selected documents are searched. This measures fixture-scoped retrieval, not open-corpus ranking, answer correctness or defense effectiveness.'))
        from app.evaluation.simple_reporting import write_csv
        write_csv(output / 'retrieval_quality.csv', list(quality[0]), quality)
        (output / 'retrieval_evaluation_status.json').write_text(json.dumps(status, indent=2) + '\n')
    print(json.dumps(status, indent=2))


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        raise SystemExit(assistant._error_text(exc)) from None
