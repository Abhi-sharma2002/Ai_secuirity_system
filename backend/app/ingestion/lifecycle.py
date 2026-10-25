"""Versioned playground ingestion using the existing verified embedding/index code."""
import hashlib
import json
import re
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from app.storage import registry as reg
from app.core.config import settings
from app.rag import indexer
from app.ingestion.parsers import parse, PARSER_VERSION

MAX_STORAGE = 200 * 1024**2


class LifecycleError(ValueError):
    def __init__(self, code, message):
        self.code = code
        super().__init__(message)


def filename(value):
    value = unicodedata.normalize('NFC', value or '')
    if not value.strip() or len(value) > 255 or '/' in value or '\\' in value or value in {'.', '..'} or any(unicodedata.category(c).startswith('C') for c in value):
        raise LifecycleError(422, 'Invalid filename: no paths, controls, or more than 255 characters')
    if Path(value).suffix.lower() not in {'.txt', '.md', '.pdf', '.docx'}:
        raise LifecycleError(415, 'Supported formats: UTF-8 TXT/MD, text PDF, non-macro DOCX')
    return value


def list_documents(*, include_deleted=False):
    with reg.connect() as db:
        rows = db.execute('''SELECT v.*, d.active_version, d.deleted FROM versions v
          JOIN documents d ON d.id=v.document_id
          WHERE d.collection='playground' AND (? OR d.deleted=0)
          ORDER BY v.created DESC''', (int(include_deleted),)).fetchall()
    return [reg.decoded(row) for row in rows]


def version(version_id):
    with reg.connect() as db:
        from app.models.contracts import DocumentVersion
        return DocumentVersion.model_validate(reg.decoded(db.execute('SELECT * FROM versions WHERE id=?', (version_id,)).fetchone())).model_dump(mode='json')


def _state(vid, state, data=None):
    with reg.connect() as db:
        if data is None:
            db.execute('UPDATE versions SET status=? WHERE id=?', (state, vid))
        else:
            db.execute('UPDATE versions SET status=?, data=? WHERE id=?', (state, json.dumps(data), vid))


def _chunks(item):
    splitter = RecursiveCharacterTextSplitter(separators=[''], chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap, add_start_index=True, strip_whitespace=False)
    chunks = []
    fingerprint = hashlib.sha256(f'{PARSER_VERSION}:{settings.chunk_size}:{settings.chunk_overlap}'.encode()).hexdigest()[:12]
    for block_number, block in enumerate(item['blocks']):
        for order, split in enumerate(splitter.split_documents([Document(page_content=block['text'])])):
            start, text = split.metadata['start_index'], split.page_content
            if not text.strip():
                continue
            cid = f"{item['id']}_{fingerprint}_{block_number}_{order}"
            chunks.append(Document(id=cid, page_content=text, metadata={
                'chunk_id': cid, 'document_id': item['document_id'], 'version_id': item['id'],
                'source': item['filename'], 'document_sha256': item['sha256'],
                'chunk_sha256': hashlib.sha256(text.encode()).hexdigest(), 'start_char': start,
                'end_char': start + len(text), 'chunk_size': settings.chunk_size,
                'chunk_overlap': settings.chunk_overlap, 'page': block['page'], 'section': block['section'],
                'parser_version': PARSER_VERSION, 'partial_text': item.get('partial_accepted', False)}))
    return chunks


def activate(vid, accept_partial=False):
    with reg.LOCK:
        item = version(vid)
        if item['status'] not in {'parsed', 'needs_review'}:
            raise LifecycleError(409, 'Version cannot be activated in its current state')
        if item['status'] == 'needs_review' and not accept_partial:
            raise LifecycleError(409, 'Explicit partial-text acceptance is required')
        data = {k: item[k] for k in ('blocks', 'warnings', 'parser_version')}
        data['partial_accepted'] = accept_partial
        item.update(data)
        _state(vid, 'indexing', data)
        try:
            result = indexer.index_documents(_chunks(item))
            with reg.connect() as db:
                doc = db.execute('SELECT * FROM documents WHERE id=?', (item['document_id'],)).fetchone()
                if doc['deleted'] or doc['active_version'] != item['expected_version']:
                    raise LifecycleError(409, 'Active version changed; previous version preserved')
                db.execute("UPDATE versions SET status='ready', index_name=? WHERE id=?", (result['collection'], vid))
                db.execute('UPDATE documents SET active_version=? WHERE id=?', (vid, item['document_id']))
        except Exception:
            _state(vid, 'failed', {**data, 'error': 'indexing_or_activation_failed'})
            raise
        return version(vid)


def ingest(file, document_id=None, expected_version=None):
    # Serial writes are intentional in the documented single-process deployment.
    with reg.LOCK:
        name = filename(file.filename)
        raw = file.file.read(settings.max_file_size + 1)
        if len(raw) > settings.max_file_size:
            raise LifecycleError(413, 'File exceeds configured byte limit')
        if not raw:
            raise LifecycleError(422, 'Empty file')
        digest = hashlib.sha256(raw).hexdigest()
        with reg.connect() as db:
            if document_id:
                doc = db.execute("SELECT * FROM documents WHERE id=? AND collection='playground' AND deleted=0", (document_id,)).fetchone()
                if not doc:
                    raise LifecycleError(404, 'Document not found')
                if not expected_version or doc['active_version'] != expected_version:
                    raise LifecycleError(409, 'Expected active version does not match')
            duplicate = db.execute('''SELECT v.* FROM versions v JOIN documents d ON d.active_version=v.id
                WHERE d.collection='playground' AND d.deleted=0 AND v.sha256=? AND v.status='ready' ''', (digest,)).fetchone()
            if duplicate:
                if document_id and duplicate['document_id'] != document_id:
                    raise LifecycleError(409, 'Content already belongs to another active document')
                return {**reg.decoded(duplicate), 'duplicate': True}
            total = sum(p.stat().st_size for p in (reg.ROOT / 'raw').glob('*')) if (reg.ROOT / 'raw').exists() else 0
            if total + len(raw) > MAX_STORAGE:
                raise LifecycleError(413, 'Storage limit reached; run documented cleanup')
            did, vid = document_id or str(uuid4()), str(uuid4())
            if not document_id:
                db.execute("INSERT INTO documents(id,collection) VALUES(?,'playground')", (did,))
            db.execute('INSERT INTO versions VALUES(?,?,?,?,?,?,?,?,?)',
                (vid, did, name, digest, 'received', datetime.now(timezone.utc).isoformat(), None, '{}', expected_version))
        rawdir = reg.ROOT / 'raw'
        rawdir.mkdir(mode=0o700, exist_ok=True)
        with (rawdir / vid).open('xb') as output:
            output.write(raw)
        (rawdir / vid).chmod(0o600)
        try:
            _state(vid, 'validating')
            _state(vid, 'parsing')
            parsed = parse(raw, Path(name).suffix.lower())
            _state(vid, parsed['status'], parsed)
            if parsed['status'] != 'parsed':
                return version(vid)
            return activate(vid)
        except ValueError as exc:
            _state(vid, 'rejected', {'error': str(exc)[:160]})
            return version(vid)
        except Exception:
            _state(vid, 'failed', {'error': 'ingestion_failed; inspect local dependencies/model availability'})
            return version(vid)


def delete(did, expected):
    with reg.LOCK, reg.connect() as db:
        row = db.execute("SELECT * FROM documents WHERE id=? AND collection='playground' AND deleted=0", (did,)).fetchone()
        if not row:
            raise LifecycleError(404, 'Document not found')
        if row['active_version'] != expected:
            raise LifecycleError(409, 'Expected version mismatch')
        db.execute('UPDATE documents SET deleted=1, active_version=NULL WHERE id=?', (did,))
        db.execute("UPDATE versions SET status='deleted' WHERE document_id=?", (did,))
    return {'document_id': did, 'status': 'deleted'}


def snapshot():
    with reg.connect() as db:
        rows = db.execute('''SELECT v.* FROM documents d JOIN versions v ON v.id=d.active_version
          WHERE d.collection='playground' AND d.deleted=0 AND v.status='ready' ''').fetchall()
    return [reg.decoded(r) for r in rows]
