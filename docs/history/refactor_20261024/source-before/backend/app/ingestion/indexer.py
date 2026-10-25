
import hashlib
import logging
import json
import re
from pathlib import Path

import chromadb
from langchain_core.documents import Document

from app.rag.embeddings import ProjectEmbeddings, validate_vectors
from app.core.config import settings
from app.models.document import valid_document_id


logger = logging.getLogger(__name__)
embed_texts = ProjectEmbeddings().embed_documents

DB_PATH = settings.db_path
COLLECTION_PREFIX = "enterprise_documents"
BATCH_SIZE = settings.batch_size


def index_configuration() -> dict:
    return {"schema_version": 2, "embedding_model": settings.embedding_model,
            "embedding_revision": settings.embedding_revision,
            "embedding_dimension": settings.embedding_dimension,
            "normalized": True, "distance_metric": "cosine"}


def get_client():
    DB_PATH.mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(path=str(DB_PATH), settings=chromadb.Settings(anonymized_telemetry=False))


def validate_chunks(chunks: list[dict]) -> None:
    if not chunks:
        raise ValueError("Cannot index an empty chunk list")

    required = {
        "chunk_id",
        "document_id",
        "source",
        "content",
        "start_char",
        "end_char",
        "document_sha256",
        "chunk_sha256",
    }

    seen_ids = set()
    chunking_configs = set()

    for chunk in chunks:
        if not isinstance(chunk, dict):
            raise ValueError("Chunks must be dictionaries")
        missing = required - chunk.keys()

        if missing:
            raise ValueError(
                f"Missing fields: {sorted(missing)}"
            )

        chunk_id = chunk["chunk_id"]

        if not isinstance(chunk_id, str) or not chunk_id:
            raise ValueError("Invalid chunk ID")

        if chunk_id in seen_ids:
            raise ValueError(
                f"Duplicate chunk ID: {chunk_id}"
            )

        seen_ids.add(chunk_id)

        for key in ("document_id", "source", "document_sha256"):
            if not isinstance(chunk[key], str) or not chunk[key].strip():
                raise ValueError(f"Invalid {key}: {chunk_id}")
        if not valid_document_id(chunk["document_id"]):
            raise ValueError("Invalid document ID")
        if not re.fullmatch(r"[0-9a-f]{64}", chunk["document_sha256"]):
            raise ValueError("Invalid document checksum")
        size = chunk.get("chunk_size", settings.chunk_size)
        overlap = chunk.get("chunk_overlap", settings.chunk_overlap)
        if type(size) is not int or type(overlap) is not int or not 0 <= overlap < size:
            raise ValueError("Invalid chunking configuration")
        chunking_configs.add((size, overlap))
        if len(chunking_configs) > 1:
            raise ValueError("Mixed chunking configurations")
        content = chunk["content"]

        if not isinstance(content, str) or not content.strip():
            raise ValueError(
                f"Empty content: {chunk_id}"
            )

        start = chunk["start_char"]
        end = chunk["end_char"]

        if (
            type(start) is not int
            or type(end) is not int
            or start < 0
            or end <= start
            or end - start != len(content)
        ):
            raise ValueError(
                f"Invalid offsets: {chunk_id}"
            )

        digest = hashlib.sha256(
            content.encode("utf-8")
        ).hexdigest()

        if digest != chunk["chunk_sha256"]:
            raise ValueError(
                f"Chunk checksum mismatch: {chunk_id}"
            )


def chunk_metadata(chunk: dict) -> dict:
    keys = ("document_id", "source", "start_char", "end_char",
            "document_sha256", "chunk_sha256", "chunk_size", "chunk_overlap",
            "version_id", "page", "section", "parser_version", "partial_text")
    metadata = {key: chunk[key] for key in keys if key in chunk}
    metadata.setdefault("chunk_size", settings.chunk_size)
    metadata.setdefault("chunk_overlap", settings.chunk_overlap)
    return metadata


def calculate_dataset_version(chunks: list[dict]) -> str:
    # Canonical encoding avoids ambiguous concatenation and versions evidence metadata.
    payload = {"configuration": index_configuration(),
               "chunks": [{"id": c["chunk_id"], **chunk_metadata(c)}
                          for c in sorted(chunks, key=lambda c: c["chunk_id"])]}
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()[:16]


def verify_records(collection, chunks: list[dict]) -> set[str]:
    records = collection.get(include=["documents", "metadatas", "embeddings"])
    ids = records["ids"]
    fields = [records.get(key) for key in ("documents", "metadatas", "embeddings")]
    if any(value is None or len(value) != len(ids) for value in fields):
        raise RuntimeError("Index contains incomplete records")
    expected = {c["chunk_id"]: c for c in chunks}
    if len(set(ids)) != len(ids) or set(ids) - expected.keys():
        raise RuntimeError("Index contains unexpected IDs; refusing to overwrite")
    for i, chunk_id in enumerate(ids):
        chunk = expected[chunk_id]
        if fields[0][i] != chunk["content"] or fields[1][i] != chunk_metadata(chunk):
            raise RuntimeError("Index evidence differs; refusing to overwrite")
        validate_vectors([list(fields[2][i])], 1)
    return set(ids)


def index_chunks(chunks: list[dict]) -> dict:
    validate_chunks(chunks)
    dataset_version = calculate_dataset_version(chunks)
    collection_name = f"{COLLECTION_PREFIX}_{dataset_version}"
    metadata = {**index_configuration(), "dataset_version": dataset_version,
                "expected_chunks": len(chunks)}
    collection = get_client().get_or_create_collection(
        name=collection_name, embedding_function=None, metadata={**metadata, "hnsw:space": "cosine", "status": "building"})
    if any((collection.metadata or {}).get(k) != v for k, v in metadata.items()):
        raise RuntimeError("Incompatible index metadata; refusing to overwrite")
    if (collection.metadata or {}).get("status") not in {"building", "verified"}:
        raise RuntimeError("Unknown index lifecycle state")
    existing = verify_records(collection, chunks)
    if (collection.metadata or {}).get("status") == "verified" and len(existing) != len(chunks):
        raise RuntimeError("Verified index is incomplete")
    pending = [c for c in chunks if c["chunk_id"] not in existing]
    logger.info("index_start collection=%s version=%s pending=%d", collection_name, dataset_version, len(pending))
    # Interrupted collections remain building and can resume after record verification.
    for start in range(0, len(pending), BATCH_SIZE):
        batch = pending[start:start + BATCH_SIZE]
        vectors = embed_texts([c["content"] for c in batch])
        validate_vectors(vectors, len(batch))
        collection.add(ids=[c["chunk_id"] for c in batch],
                       documents=[c["content"] for c in batch], embeddings=vectors,
                       metadatas=[chunk_metadata(c) for c in batch])
    actual = verify_records(collection, chunks)
    if actual != {c["chunk_id"] for c in chunks}:
        raise RuntimeError("Index verification failed: stored IDs differ")
    collection.modify(metadata={**metadata, "status": "verified"})
    logger.info("index_complete collection=%s count=%d", collection_name, len(actual))
    return {"collection": collection_name, "dataset_version": dataset_version,
            "indexed_chunks": len(actual), "status": "verified"}


def chunk_records(documents: list[Document]) -> list[dict]:
    """Adapt native chunks, rejecting conflicting identity/content metadata."""
    if not isinstance(documents, list) or any(not isinstance(doc, Document) for doc in documents):
        raise ValueError("Expected a list of LangChain chunk Documents")
    records = []
    for document in documents:
        if document.id != document.metadata.get("chunk_id"):
            raise ValueError("Chunk ID differs from metadata")
        if "content" in document.metadata:
            raise ValueError("Chunk content belongs in page_content")
        records.append({**document.metadata, "content": document.page_content})
    return records


def index_documents(documents: list[Document]) -> dict:
    """Index LangChain chunks through the same verified Chroma lifecycle."""
    return index_chunks(chunk_records(documents))
