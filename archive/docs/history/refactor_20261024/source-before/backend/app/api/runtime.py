"""Local single-user API. Benchmark mutation is intentionally CLI-only."""
import hashlib
import json
import re
from typing import Literal
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field
from starlette.concurrency import run_in_threadpool
from starlette.datastructures import UploadFile
from app.core import registry as reg
from app.ingestion import lifecycle as life
from app.llm.client import readiness
from app.rag.assistant import respond

router = APIRouter()


class Strict(BaseModel):
    model_config = ConfigDict(extra='forbid')


class Query(Strict):
    question: str = Field(min_length=1, max_length=2000)
    mode: Literal['A', 'B', 'C'] = 'B'
    collection: Literal['playground'] = 'playground'
    request_id: str = Field(pattern=r'^[a-zA-Z0-9-]{8,80}$')


class Expected(Strict):
    expected_version: str | None = None


@router.get('/health')
def health():
    return {'status': 'ok', 'scope': 'local-single-user-one-worker'}


@router.get('/ready')
def ready():
    with reg.connect() as db:
        db.execute('SELECT 1').fetchone()
    from app.core.config import settings, LiveSettings
    from app.llm import diagnostics
    try:
        config = LiveSettings.from_env()
        configuration = {**diagnostics.provenance(config), 'credentials_present': bool(config.api_key),
                         'provider': config.provider, 'model': config.model, 'base_url': config.base_url,
                         'authentication_mode': config.auth_mode, 'free_only': config.free_only,
                         'reasoning_effort': config.reasoning_effort,
                         'request_timeout_seconds': config.request_timeout_seconds,
                         'missing_configuration': [name for name, value in (
                             ('AZURE_OPENAI_API_KEY', config.api_key),
                             ('AZURE_OPENAI_ENDPOINT', config.base_url),
                             ('AZURE_OPENAI_DEPLOYMENT', config.model)) if not value]}
    except Exception:
        configuration = {'credential_source': 'not captured', 'credential_matches_root_env': None}
    return {'registry': 'ready', 'embeddings': 'lazy-loaded on ingestion/retrieval', 'live': readiness(),
            'configuration': configuration,
            'limits': {'max_file_bytes': settings.max_file_size, 'max_batch_files': 5, 'max_raw_storage_bytes': life.MAX_STORAGE, 'top_k': settings.top_k}}


@router.get('/documents')
def documents():
    # Extracted text is returned as JSON; UI renders it as plain text.
    return {'documents': life.list_documents()}


def translate(exc):
    if isinstance(exc, life.LifecycleError):
        raise HTTPException(exc.code, str(exc)) from None
    if isinstance(exc, KeyError):
        raise HTTPException(404, 'Document/version not found') from None
    raise exc


@router.post('/documents', status_code=201)
async def upload(request: Request):
    async with request.form(max_files=5, max_fields=0) as form:
        files = form.getlist('files') or form.getlist('file')
        if not 1 <= len(files) <= 5 or any(not isinstance(f, UploadFile) for f in files) or len(list(form.multi_items())) != len(files):
            raise HTTPException(422, 'Supply 1-5 files in the files field')
        outcomes = []
        for file in files:
            try:
                outcomes.append(await run_in_threadpool(life.ingest, file))
            except life.LifecycleError as exc:
                outcomes.append({'filename': file.filename, 'status': 'rejected', 'error': str(exc), 'http_status': exc.code})
        return {'outcomes': outcomes}


@router.post('/documents/{document_id}/replace')
async def replace(document_id: str, request: Request, expected_version: str):
    async with request.form(max_files=1, max_fields=0) as form:
        file = form.get('file')
        if not isinstance(file, UploadFile) or len(form) != 1:
            raise HTTPException(422, 'Supply one file')
        try:
            return await run_in_threadpool(life.ingest, file, document_id, expected_version)
        except Exception as exc:
            translate(exc)


@router.post('/versions/{version_id}/accept-partial')
def accept(version_id: str):
    try:
        return life.activate(version_id, accept_partial=True)
    except Exception as exc:
        translate(exc)


@router.delete('/documents/{document_id}')
def delete(document_id: str, expected_version: str | None = None):
    try:
        return life.delete(document_id, expected_version)
    except Exception as exc:
        translate(exc)


@router.get('/versions/{version_id}')
def status(version_id: str):
    try:
        return life.version(version_id)
    except Exception as exc:
        translate(exc)


@router.post('/search')
def search(query: Query):
    return life.search(query.question)


@router.post('/chat')
def chat(query: Query):
    fingerprint = hashlib.sha256(query.model_dump_json(exclude={'request_id'}).encode()).hexdigest()
    # Serial execution prevents duplicate live requests from reruns/retries in this process.
    with reg.LOCK:
        with reg.connect() as db:
            previous = db.execute('SELECT * FROM requests WHERE id=?', (query.request_id,)).fetchone()
            if previous:
                if previous['fingerprint'] != fingerprint:
                    raise HTTPException(409, 'Request ID already used with different input')
                return json.loads(previous['result'])
            db.execute('INSERT INTO requests VALUES(?,?,?)', (query.request_id, fingerprint,
                json.dumps({'status': 'interrupted_or_in_progress', 'error': 'This ID is reserved. Inspect call ledger before explicitly submitting a new request.'})))
        result = respond(query.question, query.mode, run_context={'client_request_id': query.request_id})
        with reg.connect() as db:
            db.execute('UPDATE requests SET result=? WHERE id=?', (json.dumps(result), query.request_id))
        return result


@router.get('/results')
def results():
    root = reg.ROOT / 'experiments'
    return {'runs': [p.name for p in root.iterdir() if p.is_dir() and (p/'experiment.json').is_file()] if root.exists() else []}


@router.get('/results/{run_id}')
def result(run_id: str):
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,80}', run_id):
        raise HTTPException(422, 'Invalid run ID')
    folder = reg.ROOT / 'experiments' / run_id
    if not (folder / 'experiment.json').is_file():
        raise HTTPException(404, 'Run not found')
    return {'experiment': json.loads((folder / 'experiment.json').read_text()),
            'results': [json.loads(p.read_text()) for p in sorted(folder.glob('case-*.json'))],
            'summary': json.loads((folder / 'summary.json').read_text()) if (folder / 'summary.json').exists() else None}


RESULT_ARTIFACTS = frozenset({
    'records.csv', 'records.json', 'comparison.csv', 'comparison.json',
    'review-template.json', 'review-packets.json', 'operational-summary.json',
    'asr.png', 'exposed_asr.png', 'benign_task_success.png',
    'benign_false_flags.png', 'benign_false_blocks.png', 'quality.png', 'latency.png'})


@router.get('/results/{run_id}/artifacts/{artifact}')
def result_artifact(run_id: str, artifact: str):
    from starlette.responses import FileResponse
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,80}', run_id) or artifact not in RESULT_ARTIFACTS:
        raise HTTPException(404, 'Unknown result artifact')
    folder = reg.ROOT / 'experiments' / run_id
    path = folder / artifact
    if (folder.is_symlink() or not (folder / 'experiment.json').is_file() or not path.is_file()
            or path.is_symlink() or not path.resolve().is_relative_to(folder.resolve())):
        raise HTTPException(404, 'Result artifact unavailable')
    media = 'image/png' if artifact.endswith('.png') else 'application/json' if artifact.endswith('.json') else 'text/csv'
    return FileResponse(path, media_type=media, filename=artifact)


@router.get('/diagnostics')
def diagnostics_list():
    folder=reg.ROOT/'diagnostics'
    return {'diagnostics':sorted(p.name for p in folder.iterdir()
        if p.is_dir() and not p.is_symlink() and (p/'operational-summary.json').is_file()) if folder.exists() else []}


@router.get('/diagnostics/{diagnostic_id}')
def diagnostic_summary(diagnostic_id: str):
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,100}',diagnostic_id):
        raise HTTPException(404,'Unknown diagnostic')
    folder=reg.ROOT/'diagnostics'/diagnostic_id
    path=folder/'operational-summary.json'
    if folder.is_symlink() or path.is_symlink() or not path.is_file():
        raise HTTPException(404,'Unknown diagnostic')
    saved=json.loads(path.read_text())
    # Return only the normal sanitized operational summary, never bindings/receipts.
    allowed={'outcome','attempts','diagnostics','remaining','expires_at','parent_stop_preserved',
             'historical_accounting_unchanged','parent_receipt_unchanged',
             'original_evaluation_artifacts_unchanged','live_disabled'}
    return {'label':'Separate provider diagnostic; not an evaluation grade',
            'summary':{k:v for k,v in saved.items() if k in allowed}}
