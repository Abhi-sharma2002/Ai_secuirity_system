"""Composable LangChain ingestion, shared with the existing validated services."""
from langchain_core.runnables import RunnableLambda, RunnableSequence

from app.core.config import settings
from app.ingestion.chunker import split_documents
from app.ingestion.indexer import index_documents


def build_ingestion_pipeline(
    chunk_size: int = settings.chunk_size,
    chunk_overlap: int = settings.chunk_overlap,
) -> RunnableSequence:
    """Accept source Documents; return a verified Chroma collection result.

    This fixture/general ingestion pipeline preserves interrupted building indexes
    for verified resumption. Uploads use their own rollback lifecycle around the
    same splitting and indexing functions.
    """
    if type(chunk_size) is not int or chunk_size <= 0:
        raise ValueError('chunk_size must be positive')
    if type(chunk_overlap) is not int or not 0 <= chunk_overlap < chunk_size:
        raise ValueError('chunk_overlap must be >= 0 and smaller than chunk_size')

    def split(sources):
        return split_documents(sources, chunk_size, chunk_overlap)

    return (RunnableLambda(split, name='split_verified_sources')
            | RunnableLambda(index_documents, name='index_verified_chunks'))
