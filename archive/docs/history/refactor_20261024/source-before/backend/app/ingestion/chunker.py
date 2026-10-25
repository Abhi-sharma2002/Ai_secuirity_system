
import hashlib
import logging

from langchain_core.documents import Document as LangChainDocument
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.core.config import settings

logger = logging.getLogger(__name__)


def chunk_documents(
    documents: list[dict | LangChainDocument],
    chunk_size: int = settings.chunk_size,
    chunk_overlap: int = settings.chunk_overlap,
) -> list[dict]:
    """
    Split documents into overlapping character-based chunks.

    Preserve source IDs, offsets, and original text.
    """

    if type(chunk_size) is not int or chunk_size <= 0:
        raise ValueError("chunk_size must be positive")

    if type(chunk_overlap) is not int or not 0 <= chunk_overlap < chunk_size:
        raise ValueError(
            "chunk_overlap must be >= 0 and smaller than chunk_size"
        )

    chunks = []
    splitter = RecursiveCharacterTextSplitter(
        separators=[""], chunk_size=chunk_size, chunk_overlap=chunk_overlap,
        strip_whitespace=False, add_start_index=True,
    )

    seen_ids = set()
    for document in documents:
        if isinstance(document, LangChainDocument):
            if document.id is not None and document.id != document.metadata.get("document_id"):
                raise ValueError("Document ID differs from metadata")
            document = {
                "content": document.page_content,
                **{key: document.metadata.get(key) for key in
                   ("document_id", "source", "sha256")},
            }
        if not isinstance(document, dict) or any(
            not isinstance(document.get(key), str) or not document[key].strip()
            for key in ("content", "document_id", "source", "sha256")
        ):
            raise ValueError("Document requires nonempty content, document_id, source and sha256")
        if document["document_id"] in seen_ids:
            raise ValueError("Duplicate document ID")
        seen_ids.add(document["document_id"])
        if hashlib.sha256(document["content"].encode("utf-8")).hexdigest() != document["sha256"]:
            raise ValueError("Document checksum mismatch")
        content = document["content"]
        document_id = document["document_id"]

        source = LangChainDocument(page_content=content, metadata={
            "document_id": document_id, "source": document["source"],
            "document_sha256": document["sha256"],
        })
        for chunk_number, split in enumerate(splitter.split_documents([source]), start=1):
            start = split.metadata["start_index"]
            text = split.page_content
            end = start + len(text)
            if start < 0 or content[start:end] != text:
                raise ValueError("Text splitter returned invalid source offsets")

            chunk_id = f"{document_id}_chunk_{chunk_number:03d}"

            chunks.append({
                "chunk_id": chunk_id,
                "document_id": document_id,
                "source": document["source"],
                "content": text,
                "start_char": start,
                "end_char": end,
                "document_sha256": document["sha256"],
                "chunk_size": chunk_size,
                "chunk_overlap": chunk_overlap,
                "chunk_sha256": hashlib.sha256(
                    text.encode("utf-8")
                ).hexdigest(),
            })

            if end == len(content):
                break

    logger.info("chunks_generated count=%d", len(chunks))
    return chunks


def split_documents(
    documents: list[LangChainDocument],
    chunk_size: int = settings.chunk_size,
    chunk_overlap: int = settings.chunk_overlap,
) -> list[LangChainDocument]:
    """Native LangChain chunk output with the existing verified chunk schema."""
    if not isinstance(documents, list) or any(
        not isinstance(document, LangChainDocument) for document in documents
    ):
        raise ValueError("Expected a list of LangChain Documents")
    return [LangChainDocument(
        id=chunk["chunk_id"], page_content=chunk["content"],
        metadata={key: value for key, value in chunk.items() if key != "content"},
    ) for chunk in chunk_documents(documents, chunk_size, chunk_overlap)]
