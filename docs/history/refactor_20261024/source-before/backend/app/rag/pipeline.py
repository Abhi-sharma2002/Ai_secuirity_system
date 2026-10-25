"""LangChain retrieval pipeline over the project's verified Chroma evidence.

Returns evidence only. The shared LLM client and fixed-context baseline are separate.
"""
from dataclasses import asdict

from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever
from pydantic import ConfigDict, Field

from app.core.config import settings
from app.models.document import valid_document_id
from app.rag.retriever import DocumentRetriever


class EvidenceRetriever(BaseRetriever):
    """Runnable adapter retaining integrity checks and application-owned scope.

    Construct with IDs selected by trusted application code, never an LLM/tool.
    This scope is a retrieval filter, not authentication.
    """
    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)
    backend: DocumentRetriever = Field(exclude=True)
    allowed_document_ids: frozenset[str]
    top_k: int = Field(default=settings.top_k, strict=True, ge=1, le=20)

    def _get_relevant_documents(self, query: str, *, run_manager) -> list[Document]:
        hits = self.backend.search(query, self.allowed_document_ids, self.top_k)
        documents = []
        for hit in hits:
            metadata = asdict(hit)
            content = metadata.pop('content')
            documents.append(Document(id=hit.chunk_id, page_content=content, metadata=metadata))
        return documents


def build_retrieval_pipeline(collection_name: str, allowed_document_ids: set[str] | frozenset[str],
                             top_k: int = settings.top_k) -> EvidenceRetriever:
    """Build once for a trusted scope, then call invoke(question) or batch([...])."""
    if not isinstance(allowed_document_ids, (set, frozenset)) or any(
        not valid_document_id(item) for item in allowed_document_ids
    ):
        raise ValueError('Expected a trusted set of document IDs')
    if not allowed_document_ids:
        raise PermissionError('No documents authorized for retrieval')
    return EvidenceRetriever(backend=DocumentRetriever(collection_name),
                             allowed_document_ids=frozenset(allowed_document_ids), top_k=top_k)
