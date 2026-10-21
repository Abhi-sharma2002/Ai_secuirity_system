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
    from app.core.config import settings
    return {'registry': 'ready', 'embeddings': 'lazy-loaded on ingestion/retrieval', 'live': readiness(),
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
    return {'runs': [p.name for p in root.iterdir() if p.is_dir()] if root.exists() else []}


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
