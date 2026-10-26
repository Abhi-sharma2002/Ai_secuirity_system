"""Plan or run one isolated, synthetic Azure A/B/C integration check.

Running requires a separately authorized current four-call trial receipt.
This never creates/renews authorization or writes benchmark results.
"""
import argparse
import json
import logging
import os
from pathlib import Path
import re
import sys
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[2]
FACT = 'The fictional ORCHID-LOCAL policy grants 3 study leave days.'
QUESTION = 'How many study leave days does the fictional ORCHID-LOCAL policy grant?'
ORDER = [('A', 'generation'), ('B', 'generation'), ('C', 'screening'), ('C', 'generation')]


def plan():
    return {'scope': 'Synthetic integration only; no attack benchmark or user documents',
            'document': FACT, 'question': QUESTION, 'provider': 'azure_openai',
            'model': 'gpt-5-mini', 'temperature_sent': False,
            'max_completion_tokens': 700, 'request_timeout_seconds': 30,
            'request_order': ORDER, 'maximum_provider_attempts': len(ORDER),
            'maximum_reserved_units': len(ORDER) * 32000,
            'automatic_retries': 0, 'stop_on_first_failure': True,
            'minimum_seconds_between_completed_calls': 65,
            'live_authorization_created': False}


def run(workspace):
    workspace = workspace.resolve()
    if not workspace.is_relative_to((ROOT / '.private').resolve()) or workspace.exists():
        raise ValueError('Choose a new private workspace; prior runs are never overwritten')
    # Set storage paths before importing the app. The live gate remains intact.
    os.environ.update(APP_DATA_DIRECTORY=str(workspace / 'runtime'),
                      CHROMA_DB_PATH=str(workspace / 'chroma'),
                      UPLOAD_DIRECTORY=str(workspace / 'uploads'),
                      DOCUMENT_DIRECTORY=str(workspace / 'documents'),
                      HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1',
                      ANONYMIZED_TELEMETRY='False', OPENROUTER_API_KEY='')
    logging.getLogger('dotenv.main').setLevel(logging.CRITICAL)
    sys.path.insert(0, str(ROOT / 'backend'))
    from app.core.config import LiveSettings
    from app.llm import client as live
    from app.evaluation.simple_config import load_config
    from app.main import app
    from scripts.azure_live_integration import Bound
    from fastapi.testclient import TestClient
    from unittest.mock import patch

    config = LiveSettings.from_env()
    shared = load_config()
    if (not config.enabled or not config.free_only or config.provider != shared['provider']
            or config.model != shared['model'] or config.request_timeout_seconds != 30):
        raise ValueError('Requires explicitly enabled current Azure trial settings matching the shared configuration')
    workspace.mkdir(parents=True, mode=0o700)
    workspace.chmod(0o700)
    approved = live.approval()
    capacity = live.allowance_capacity(approved)
    if (approved.max_calls != len(ORDER) or approved.max_reserved_tokens != len(ORDER) * 32000
            or capacity['remaining_calls'] != len(ORDER) or capacity['stopped']):
        raise ValueError('Requires a fresh explicitly authorized four-call trial receipt; no renewal or extra capacity')
    bound = Bound(workspace, ORDER, len(ORDER) * 32000)
    summary = {'plan': plan(), 'passed': False, 'modes': {}}
    try:
        with TestClient(app) as api, patch.object(live, 'reserve', bound.reserve), patch.object(live, 'call', bound.call):
            upload = api.post('/documents', files={'files': ('Fictional Azure smoke policy.txt', FACT.encode())})
            upload.raise_for_status()
            document = upload.json()['outcomes'][0]
            if document['status'] != 'ready':
                raise RuntimeError('Synthetic document ingestion failed; no provider call')
            evidence_ids = None
            for mode in 'ABC':
                response = api.post('/chat', json={'question': QUESTION, 'mode': mode,
                    'request_id': str(uuid4()), 'external_processing_confirmed': True})
                response.raise_for_status()
                result = response.json()
                # Raw synthetic responses remain private, never printed.
                (workspace / f'{mode}.json').write_text(json.dumps(result, indent=2))
                ids = [h['id'] for h in result.get('candidate_evidence', [])]
                if evidence_ids is None:
                    evidence_ids = ids
                supported = (result.get('status') == 'answered'
                    and bool(re.search(r'\b(3|three)\b', result.get('answer', ''), re.IGNORECASE))
                    and any(h.get('document_id') == document['document_id'] for h in result.get('references', [])))
                summary['modes'][mode] = {'status': result.get('status'), 'expected_fact_and_source': supported,
                                         'same_initial_evidence': ids == evidence_ids}
                if not supported or ids != evidence_ids:
                    raise RuntimeError('Integration failed; inspect private evidence; no retry or further mode')
            summary['passed'] = len(bound.data['attempts']) == len(ORDER)
    finally:
        summary['provider_attempts'] = len(bound.data['attempts'])
        summary['reserved_calls'] = bound.data['reserved_calls']
        (workspace / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    print(json.dumps(summary, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    choices = parser.add_mutually_exclusive_group(required=True)
    choices.add_argument('--plan', action='store_true')
    choices.add_argument('--run', action='store_true')
    parser.add_argument('--workspace', type=Path)
    args = parser.parse_args()
    if args.plan:
        print(json.dumps(plan(), indent=2))
    elif args.workspace:
        run(args.workspace)
    else:
        parser.error('--run requires --workspace')


if __name__ == '__main__':
    main()
