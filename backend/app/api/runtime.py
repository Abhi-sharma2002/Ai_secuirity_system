"""Local single-user API with explicit human review; provider evaluation is CLI-only."""
from app.rag import retrieval
import hashlib
import json
import re
from typing import Literal
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field
from starlette.concurrency import run_in_threadpool
from starlette.datastructures import UploadFile
from app.storage import registry as reg
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
    external_processing_confirmed: bool = Field(default=False, strict=True)
    document_id: str | None = Field(default=None, min_length=1, max_length=100)


def selected_documents(query):
    if query.document_id is None:
        return None
    items = [item for item in life.snapshot() if item['document_id'] == query.document_id]
    if not items:
        raise HTTPException(409, 'Selected document is no longer active. Choose an available document.')
    return items


def query_fingerprint(query):
    excluded = {'request_id'} | ({'document_id'} if query.document_id is None else set())
    return query.model_dump_json(exclude=excluded)


class Expected(Strict):
    expected_version: str | None = None


class HumanQualityReview(Strict):
    case_id: str = Field(min_length=1, max_length=100)
    mode: Literal['A', 'B', 'C']
    record_sha256: str = Field(pattern=r'^[0-9a-f]{64}$')
    reviewer: str = Field(min_length=1, max_length=80)
    quality_0_4: int = Field(ge=0, le=4, strict=True)
    task_correct: bool = Field(strict=True)
    attack_correct: bool | None = Field(default=None, strict=True)


class HumanCaseReview(Strict):
    case_id: str = Field(min_length=1, max_length=100)
    mode: Literal['A', 'B', 'C']
    record_sha256: str = Field(pattern=r'^[0-9a-f]{64}$')
    reviewer: str = Field(min_length=1, max_length=80)
    rationale: str = Field(min_length=1, max_length=2000)
    task_passed: bool = Field(strict=True)
    attack_succeeded: bool | None = Field(default=None, strict=True)
    answer_chunk_removed: bool | None = Field(default=None, strict=True)


def refresh_evaluation_reports():
    from app.evaluation.simple_config import ROOT
    from app.evaluation.simple_reporting import make_report, manifest, read_records
    from app.evaluation.simple_documents import write_documents
    from app.evaluation.case_audit import write_case_audit
    output = ROOT / 'results'
    make_report(output / 'records.csv', output)
    # The case audit requires actual retrieval traces, which live runs retain.
    if (output / 'retrieval').is_dir():
        data = manifest()
        write_case_audit(output, output / 'records.csv', read_records(output / 'records.csv', data), data)
    write_documents(output, ROOT / 'docs', False)


@router.post('/evaluation-v3/quality-review')
def quality_review(review: HumanQualityReview):
    from app.evaluation.simple_config import ROOT, EvaluationError
    from app.evaluation.simple_review import submit_quality
    try:
        result = submit_quality(ROOT / 'results/records.csv', ROOT / 'results', **review.model_dump())
    except EvaluationError as exc:
        raise HTTPException(409, str(exc)) from None
    try:
        refresh_evaluation_reports()
    except Exception:
        result['report_refresh'] = 'Review saved. Regenerate reports locally before using downloaded charts.'
    return result


@router.post('/evaluation-v3/case-review')
def case_review(review: HumanCaseReview):
    from app.evaluation.simple_config import ROOT, EvaluationError
    from app.evaluation.simple_review import submit_judgment
    try:
        result = submit_judgment(ROOT / 'results/records.csv', ROOT / 'results', **review.model_dump())
    except EvaluationError as exc:
        raise HTTPException(409, str(exc)) from None
    try:
        refresh_evaluation_reports()
    except Exception:
        result['report_refresh'] = 'Decision saved. Regenerate reports locally before using downloaded charts.'
    return result


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
        required = ((
            ('AZURE_OPENAI_API_KEY', config.api_key),
            ('AZURE_OPENAI_ENDPOINT', config.base_url),
            ('AZURE_OPENAI_DEPLOYMENT', config.model),
        ) if config.provider == 'azure_openai' else (
            ('OPENROUTER_API_KEY', config.api_key),
            ('OPENROUTER_MODEL', config.model),
        ))
        configuration = {**diagnostics.provenance(config), 'credentials_present': bool(config.api_key),
                         'provider': config.provider, 'model': config.model, 'base_url': config.base_url,
                         'authentication_mode': config.auth_mode, 'free_only': config.free_only,
                         'reasoning_effort': config.reasoning_effort,
                         'request_timeout_seconds': config.request_timeout_seconds,
                         'missing_configuration': [name for name, value in required if not value]}
    except Exception:
        configuration = {'credential_source': 'not captured', 'credential_matches_root_env': None}
    return {'registry': 'ready', 'embeddings': 'lazy-loaded on ingestion/retrieval', 'live': readiness(),
            'configuration': configuration,
            'limits': {'max_file_bytes': settings.max_file_size, 'max_batch_files': 5, 'max_raw_storage_bytes': life.MAX_STORAGE, 'top_k': settings.top_k}}


@router.get('/documents')
def documents(include_deleted: bool = False):
    # Extracted text is returned as JSON; UI renders it as plain text.
    return {'documents': life.list_documents(include_deleted=include_deleted)}


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
    items = selected_documents(query)
    return retrieval.search(query.question) if items is None else retrieval.search(query.question, items)


@router.post('/chat')
def chat(query: Query):
    fingerprint = hashlib.sha256(query_fingerprint(query).encode()).hexdigest()
    # Serial execution prevents duplicate live requests from reruns/retries in this process.
    with reg.LOCK:
        items = selected_documents(query)
        with reg.connect() as db:
            previous = db.execute('SELECT * FROM requests WHERE id=?', (query.request_id,)).fetchone()
            if previous:
                if previous['fingerprint'] != fingerprint:
                    raise HTTPException(409, 'Request ID already used with different input')
                return json.loads(previous['result'])
            db.execute('INSERT INTO requests VALUES(?,?,?)', (query.request_id, fingerprint,
                json.dumps({'status': 'interrupted_or_in_progress', 'error': 'This ID is reserved. Inspect call ledger before explicitly submitting a new request.'})))
        result = respond(query.question, query.mode, snapshot_items=items, run_context={
            'client_request_id': query.request_id,
            'external_processing_confirmed': query.external_processing_confirmed,
        })
        with reg.connect() as db:
            db.execute('UPDATE requests SET result=? WHERE id=?', (json.dumps(result), query.request_id))
        return result


@router.post('/compare')
def compare_query(query: Query):
    from app.rag.comparison import compare
    fingerprint = hashlib.sha256(('benign-compare-v1:' + query_fingerprint(query)).encode()).hexdigest()
    with reg.LOCK:
        items = selected_documents(query)
        with reg.connect() as db:
            previous = db.execute('SELECT * FROM requests WHERE id=?', (query.request_id,)).fetchone()
            if previous:
                if previous['fingerprint'] != fingerprint:
                    raise HTTPException(409, 'Request ID already used with different input')
                return json.loads(previous['result'])
            db.execute('INSERT INTO requests VALUES(?,?,?)', (query.request_id, fingerprint,
                json.dumps({'status':'interrupted_or_in_progress','error':'Comparison ID reserved. No automatic replay.'})))
        result = compare(query.question, query.request_id,
                         external_processing_confirmed=query.external_processing_confirmed, snapshot_items=items)
        with reg.connect() as db:
            db.execute('UPDATE requests SET result=? WHERE id=?', (json.dumps(result), query.request_id))
        return result


@router.get('/results')
def results():
    root = reg.ROOT / 'experiments'
    return {'runs': [p.name for p in root.iterdir() if p.is_dir() and (p/'experiment.json').is_file()] if root.exists() else []}


@router.get('/evaluation-v3')
def evaluation_dashboard():
    from app.evaluation.simple_dashboard import snapshot
    try:
        return snapshot()
    except Exception:
        raise HTTPException(409, 'Evaluation files are invalid, changing or incompatible. Validate local records and regenerate the report before refreshing.') from None


@router.get('/evaluation-v3/artifacts/{artifact}')
def evaluation_artifact(artifact: str):
    from starlette.responses import FileResponse
    from app.evaluation.simple_dashboard import artifact_path, derived_artifact_current, CHARTS
    try:
        path = artifact_path(artifact)
    except FileNotFoundError:
        raise HTTPException(404, 'Evaluation artifact unavailable') from None
    if not derived_artifact_current(artifact):
        raise HTTPException(409, 'Evaluation evidence is stale; regenerate its local audit/report')
    if (artifact in CHARTS or artifact.startswith('case_evaluation.') or artifact == 'CASE_EVALUATION.md') and not evaluation_dashboard()['charts_current']:
        raise HTTPException(409, 'Evaluation artifacts are stale; regenerate the local report')
    media = 'image/png' if artifact.endswith('.png') else 'application/json' if artifact.endswith('.json') else 'text/csv' if artifact.endswith('.csv') else 'text/markdown'
    return FileResponse(path, media_type=media, filename=artifact)


@router.get('/evaluation-v3/evidence/{case_id}')
def evaluation_evidence(case_id: str):
    from app.evaluation.simple_dashboard import evidence
    try:
        return evidence(case_id)
    except FileNotFoundError:
        raise HTTPException(404, 'No saved evaluation evidence') from None
    except Exception:
        raise HTTPException(409, 'Saved evaluation evidence is invalid') from None


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


@router.get('/evaluation-document-privacy')
def document_privacy_dashboard():
    from app.evaluation.document_suite import snapshot
    try:
        return snapshot()
    except Exception:
        raise HTTPException(409, 'Document privacy suite unavailable or inconsistent. Validate the suite locally.') from None


class DocumentPrivacyReview(Strict):
    case_id: str
    mode: Literal['A', 'B', 'C']
    record_sha256: str
    reviewer: str
    rationale: str
    leaked: bool
    task_passed: bool


@router.post('/evaluation-document-privacy/review')
def document_privacy_review(review: DocumentPrivacyReview):
    from app.evaluation.document_suite import submit_review
    try:
        return submit_review(**review.model_dump())
    except (ValueError, OSError):
        raise HTTPException(409, 'Review unavailable or record changed. Refresh and complete all review fields.') from None
