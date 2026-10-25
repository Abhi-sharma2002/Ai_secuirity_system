"""Shared evidence retrieval. The application must supply a trusted allowlist.

Document IDs are a filter, not authentication or a complete authorization system.
No document screening or instruction execution occurs here.
"""
import hashlib
import logging
import math
import re
from dataclasses import dataclass
from time import perf_counter

from app.core.config import settings
from app.models.document import valid_document_id
from app.rag.indexer import get_client, index_configuration
from app.rag.embeddings import ProjectEmbeddings

logger = logging.getLogger(__name__)
embed_texts = ProjectEmbeddings().embed_documents


@dataclass(frozen=True)
class RetrievedChunk:
    chunk_id: str
    document_id: str
    source: str
    content: str
    distance: float
    start_char: int
    end_char: int
    document_sha256: str = ""
    chunk_sha256: str = ""


class DocumentRetriever:
    def __init__(self, collection_name: str):
        if not isinstance(collection_name, str) or not re.fullmatch(r'enterprise_documents_[0-9a-f]{16}', collection_name):
            raise ValueError('Invalid collection name')
        self.collection = get_client().get_collection(name=collection_name, embedding_function=None)
        self._validate_collection()

    def _validate_collection(self) -> None:
        metadata = self.collection.metadata or {}
        if metadata.get('status') != 'verified' or any(
            metadata.get(k) != v for k, v in index_configuration().items()
        ):
            raise RuntimeError('Collection is unverified or incompatible; ingest into a new version')
        if metadata.get('dataset_version') != self.collection.name.removeprefix('enterprise_documents_'):
            raise RuntimeError('Collection dataset version mismatch')
        count = self.collection.count()
        if not count or metadata.get('expected_chunks') != count:
            raise RuntimeError('Collection is empty or incomplete')

    def search(self, question: str, allowed_document_ids: set[str],
               top_k: int = settings.top_k) -> list[RetrievedChunk]:
        """Search only IDs authorized by a trusted application layer."""
        if not isinstance(question, str) or not question.strip():
            raise ValueError('Question must be a nonempty string')
        if type(top_k) is not int or not 1 <= top_k <= 20:
            raise ValueError('top_k must be an integer between 1 and 20')
        if not isinstance(allowed_document_ids, (set, frozenset)) or any(
            not isinstance(item, str) or not valid_document_id(item)
            for item in allowed_document_ids
        ):
            raise ValueError('Expected a trusted set of document IDs')
        if not allowed_document_ids:
            raise PermissionError('No documents authorized for retrieval')
        started = perf_counter()
        self._validate_collection()
        result = self.collection.query(
            query_embeddings=embed_texts([question]),
            n_results=min(top_k, self.collection.count()),
            where={'document_id': {'$in': sorted(allowed_document_ids)}},
            include=['documents', 'metadatas', 'distances'])
        try:
            rows = [result[key][0] for key in ('ids', 'documents', 'metadatas', 'distances')]
            if len({len(row) for row in rows}) != 1:
                raise ValueError('Mismatched result lengths')
            hits = []
            for chunk_id, content, metadata, distance in zip(*rows):
                if metadata['document_id'] not in allowed_document_ids:
                    raise ValueError('Authorization filter violation')
                if (not isinstance(chunk_id, str) or not chunk_id or
                    not isinstance(content, str) or not content or
                    not isinstance(metadata['source'], str) or not metadata['source'] or
                    type(metadata['start_char']) is not int or
                    type(metadata['end_char']) is not int or
                    metadata['start_char'] < 0 or
                    metadata['end_char'] - metadata['start_char'] != len(content) or
                    isinstance(distance, bool) or not math.isfinite(distance) or
                    not -1e-6 <= distance <= 2.000001):
                    raise ValueError('Invalid retrieved evidence')
                if (hashlib.sha256(content.encode('utf-8')).hexdigest() != metadata['chunk_sha256'] or
                    not isinstance(metadata['document_sha256'], str) or
                    not re.fullmatch(r'[0-9a-f]{64}', metadata['document_sha256'])):
                    raise ValueError('Retrieved evidence checksum mismatch')
                hits.append(RetrievedChunk(chunk_id, metadata['document_id'], metadata['source'],
                                           content, distance, metadata['start_char'], metadata['end_char'],
                                           metadata['document_sha256'], metadata['chunk_sha256']))
        except (KeyError, TypeError, IndexError, ValueError) as exc:
            raise RuntimeError('Invalid retrieval response') from exc
        logger.info('retrieval_completed count=%d duration=%.3f', len(hits), perf_counter() - started)
        return sorted(hits, key=lambda item: (item.distance, item.chunk_id))
