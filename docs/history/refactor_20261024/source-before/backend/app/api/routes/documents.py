"""Synchronous local upload API; original filenames are untrusted metadata."""
from fastapi import APIRouter, HTTPException, Request
from starlette.datastructures import UploadFile
from starlette.concurrency import run_in_threadpool

from app.ingestion.uploads import UploadError, ingest_upload

router = APIRouter()


@router.post('/documents', status_code=201, openapi_extra={
    'requestBody': {'required': True, 'content': {'multipart/form-data': {
        'schema': {'type': 'object', 'required': ['file'], 'properties': {
            'file': {'type': 'string', 'format': 'binary'}}}}}}})
async def upload_document(request: Request):
    # Form context closes every parsed file, including rejected extra fields/files.
    async with request.form(max_files=1, max_fields=0) as form:
        file = form.get('file')
        if len(form) != 1 or not isinstance(file, UploadFile):
            raise HTTPException(422, 'Provide one document in the file field')
        try:
            return await run_in_threadpool(ingest_upload, file)
        except UploadError as exc:
            raise HTTPException(exc.status_code, str(exc)) from exc
        except Exception as exc:
            raise HTTPException(500, 'Document processing failed') from exc
