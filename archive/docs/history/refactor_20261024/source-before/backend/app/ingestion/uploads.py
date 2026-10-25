"""Separate upload ingestion. Content checks are format checks, never screening."""
import hashlib
import json
import logging
import shutil
from uuid import uuid4

from app.core.config import settings
from app.ingestion.loader import Document
from app.ingestion.chunker import split_documents
from app.ingestion import indexer

logger = logging.getLogger(__name__)


class UploadError(ValueError):
    def __init__(self, status_code, detail):
        self.status_code = status_code
        super().__init__(detail)


def ingest_upload(file, directory=None, max_size=None):
    """Blocking operation; caller owns closing the file on every path."""
    directory = directory if directory is not None else settings.upload_directory
    max_size = max_size if max_size is not None else settings.max_file_size
    document_id = str(uuid4())
    size = 0
    workspace = None
    collection_name = None
    try:
        filename = file.filename
        if not filename or not filename.strip():
            raise UploadError(422, 'A filename is required')
        if not filename.lower().endswith('.txt'):
            raise UploadError(415, 'Only UTF-8 .txt documents are supported')
        # Original names are metadata only, including any path-like components.
        if len(filename) > 255 or any(ord(c) < 32 or ord(c) == 127 for c in filename):
            raise UploadError(422, 'Invalid filename')
        raw = bytearray()
        while True:
            block = file.file.read(min(65536, max_size + 1 - size))
            if not block:
                break
            raw.extend(block)
            size += len(block)
            if size > max_size:
                raise UploadError(413, 'Document exceeds configured size limit')
        try:
            content = raw.decode('utf-8', errors='strict')
        except UnicodeDecodeError as exc:
            raise UploadError(422, 'Document must contain valid UTF-8 text') from exc
        if not content.strip() or not content.lstrip('\ufeff').strip():
            raise UploadError(422, 'Document must contain nonempty text')
        if any((ord(c) < 32 and c not in '\t\n\r') or 127 <= ord(c) <= 159 for c in content):
            raise UploadError(422, 'Unsupported binary or control content')
        if content.lstrip().startswith(('%PDF-', 'PK\x03\x04', '{\\rtf')):
            raise UploadError(415, 'Unsupported document format; provide plain UTF-8 text')
        document = Document(document_id, filename, content, hashlib.sha256(raw).hexdigest(), size)
        chunks = split_documents([document.to_langchain()])
        directory.mkdir(parents=True, exist_ok=True)
        target = directory / document_id
        target.mkdir()  # exclusive; UUID collision cannot overwrite another upload
        workspace = target
        with (workspace / 'content.txt').open('xb') as output:
            output.write(raw)
        collection_name = f'{indexer.COLLECTION_PREFIX}_{indexer.calculate_dataset_version(indexer.chunk_records(chunks))}'
        logger.info('upload_processing id=%s bytes=%d', document_id, size)
        result = indexer.index_documents(chunks)
        metadata = dict(document_id=document_id, original_filename=filename,
                        sha256=document.sha256, size_bytes=size, **result)
        metadata['status'] = 'ready'
        with (workspace / 'metadata.json').open('x', encoding='utf-8') as output:
            json.dump(metadata, output, ensure_ascii=True)
        logger.info('upload_ready id=%s bytes=%d', document_id, size)
        return metadata
    except BaseException as exc:
        logger.warning('upload_failed id=%s bytes=%d error_type=%s',
                       document_id, size, type(exc).__name__)
        if collection_name is not None:
            # Each upload has its own UUID-derived collection, isolated from fixtures.
            try:
                indexer.get_client().delete_collection(collection_name)
            except Exception:
                logger.error('upload_index_cleanup_failed id=%s', document_id)
        if workspace is not None:
            shutil.rmtree(workspace)
        raise
