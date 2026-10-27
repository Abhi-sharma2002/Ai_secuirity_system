"""Versioned human criteria for future legacy execution; no automatic grading."""
import hashlib
import json

from app.evaluation.dataset import read_json

from app.core.environment import PROJECT_ROOT as ROOT
RUBRIC = ROOT / 'backend/benchmark/revisions/legacy-e037-task-v2/rubric.json'


def for_case(case):
    """Bind only original fixed-context E037, before execution/provider I/O.

    Keep the loader's original records unchanged. Other cases retain their old
    schema. Saved executions carry their own immutable-in-history criteria;
    reading an old result never invokes this function.
    """
    if case.get('test_id') != 'E037':
        return None
    rubric = read_json(RUBRIC)
    fingerprint = hashlib.sha256(json.dumps(case, sort_keys=True, ensure_ascii=True).encode()).hexdigest()
    if (rubric['version'] != 'legacy-e037-task-v2' or rubric['test_id'] != 'E037'
            or case.get('evidence_mode') != 'fixed_context'
            or fingerprint != rubric['original_case_sha256']):
        raise ValueError('Legacy rubric input differs; explicit new version/review required')
    return {'version': rubric['version'], 'sha256': hashlib.sha256(RUBRIC.read_bytes()).hexdigest(),
            'population': 'historical-fixed-context', 'source_case_sha256': fingerprint,
            'criteria': rubric}
