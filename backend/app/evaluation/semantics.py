"""Human-approved evaluator sidecar; never included in model evidence/prompts."""
import hashlib
from pathlib import Path

from app.evaluation.dataset import read_json

ROOT = Path(__file__).resolve().parents[3]
RULES = ROOT / 'backend/benchmark/revisions/phase12-approved-v1/rules.json'


def snapshot():
    rules = read_json(RULES)
    for relative, expected in rules['bindings'].items():
        if hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() != expected:
            raise ValueError('Approved semantic inputs changed; new version/review required')
    return {'version': rules['version'],
            'sha256': hashlib.sha256(RULES.read_bytes()).hexdigest(), 'rules': rules}


def criteria(frozen, case_id):
    rules = frozen['rules']
    result = {'version': frozen['version'], 'sha256': frozen['sha256'],
              'case_annotations': rules['case_annotations'].get(case_id, {}),
              'dataset_role': rules['dataset_role']}
    if 'component_locations' in result['case_annotations']:
        result['exposure_schema'] = rules['exposure_schema']
    return result
