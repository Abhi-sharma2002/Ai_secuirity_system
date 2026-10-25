"""CPU embeddings, cached per process and validated before storage or search."""
import logging
import math
from functools import lru_cache
from threading import Lock
from time import perf_counter

from langchain_core.embeddings import Embeddings

from app.core.config import settings

logger = logging.getLogger(__name__)
EMBEDDING_MODEL = settings.embedding_model
_model_lock = Lock()


@lru_cache(maxsize=1)
def get_embedding_model():
    # Import lazily so validation and unit tests need no model download.
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(EMBEDDING_MODEL, device='cpu', revision=settings.embedding_revision)


def validate_vectors(vectors: list[list[float]], count: int) -> None:
    if len(vectors) != count:
        raise RuntimeError('Embedding count does not match input count')
    for vector in vectors:
        if len(vector) != settings.embedding_dimension:
            raise RuntimeError('Unexpected embedding dimension')
        if not all(math.isfinite(value) for value in vector):
            raise RuntimeError('Embedding contains non-finite values')
        norm = math.sqrt(sum(value * value for value in vector))
        if not math.isclose(norm, 1.0, abs_tol=1e-3):
            raise RuntimeError('Embedding must have unit norm')


def embed_texts(texts: list[str]) -> list[list[float]]:
    if not isinstance(texts, list) or any(not isinstance(t, str) or not t.strip() for t in texts):
        raise ValueError('Embedding input must be a list of nonempty strings')
    if not texts:
        return []
    started = perf_counter()
    try:
        # lru_cache alone can initialize twice on concurrent first calls.
        with _model_lock:
            model = get_embedding_model()
        vectors = model.encode(texts, batch_size=settings.batch_size,
                               normalize_embeddings=True, convert_to_numpy=True,
                               show_progress_bar=False).tolist()
        validate_vectors(vectors, len(texts))
    except Exception as exc:
        raise RuntimeError('Embedding generation failed') from exc
    logger.info('embedding_completed count=%d duration=%.3f', len(texts), perf_counter() - started)
    return vectors


class ProjectEmbeddings(Embeddings):
    """LangChain interface backed by the pinned, validated local CPU model."""

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return embed_texts(texts)

    def embed_query(self, text: str) -> list[float]:
        return embed_texts([text])[0]
