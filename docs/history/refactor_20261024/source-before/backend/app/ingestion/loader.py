
import hashlib
import logging
import os
import re
import stat

from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Iterator

from langchain_core.document_loaders import BaseLoader
from langchain_core.documents import Document as LangChainDocument

from app.core.config import settings


logger = logging.getLogger(__name__)

DOCUMENT_PATTERN = re.compile(
    r"^(D[0-9]{3})(?:_[A-Za-z0-9_-]+)?\.txt$"
)

DEFAULT_MAX_FILE_SIZE = 5 * 1024 * 1024


class DocumentLoadError(Exception):
    """Raised when document ingestion fails."""


@dataclass(frozen=True)
class Document:
    document_id: str
    source: str
    content: str
    sha256: str
    size_bytes: int

    def to_dict(self) -> dict:
        return asdict(self)

    def to_langchain(self) -> LangChainDocument:
        """Preserve source text and provenance in LangChain's document format."""
        metadata = self.to_dict()
        content = metadata.pop("content")
        return LangChainDocument(id=self.document_id, page_content=content, metadata=metadata)


class DocumentLoader(BaseLoader):
    """LangChain fixture loader with strict filenames and byte integrity checks.

    load()/lazy_load() return LangChain Documents. The existing dictionary and
    dataclass interfaces remain available for ingestion and evaluation callers.
    Normal-filename user uploads use the separate uploads service.
    """

    def __init__(
        self,
        directory: str = str(settings.document_directory),
        max_file_size: int = settings.max_file_size,
        ignored_filenames: tuple[str, ...] = settings.ignored_document_entries,
    ):
        self.directory = Path(directory)
        self.max_file_size = max_file_size
        self.ignored_filenames = frozenset(ignored_filenames)

        if type(max_file_size) is not int or max_file_size <= 0:
            raise ValueError(
                "max_file_size must be positive"
            )

    def _validate_directory(self) -> None:
        if self.directory.is_symlink():
            raise DocumentLoadError(
                "Document directory cannot be a symlink"
            )

        if not self.directory.is_dir():
            raise DocumentLoadError(
                f"Document directory not found: "
                f"{self.directory}"
            )

    @staticmethod
    def _extract_document_id(filename: str) -> str:
        match = DOCUMENT_PATTERN.fullmatch(filename)

        if not match:
            raise DocumentLoadError(
                f"Invalid document filename: {filename}"
            )

        return match.group(1)

    def _read_document(self, path: Path) -> tuple:
        # O_NOFOLLOW prevents following a symlink
        # at the final path component on Linux.
        flags = os.O_RDONLY | os.O_NONBLOCK

        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW

        try:
            fd = os.open(path, flags)

            with os.fdopen(fd, "rb") as file:
                file_stat = os.fstat(file.fileno())

                if not stat.S_ISREG(file_stat.st_mode):
                    raise DocumentLoadError(
                        f"Not a regular file: {path.name}"
                    )

                if file_stat.st_size > self.max_file_size:
                    raise DocumentLoadError(
                        f"File exceeds size limit: {path.name}"
                    )

                # Read at most limit + 1 bytes to detect
                # files that grow during ingestion.
                raw = file.read(self.max_file_size + 1)

                if len(raw) > self.max_file_size:
                    raise DocumentLoadError(
                        f"File exceeds size limit: {path.name}"
                    )

                if not raw:
                    raise DocumentLoadError(
                        f"Empty document: {path.name}"
                    )

        except OSError as exc:
            raise DocumentLoadError(
                f"Cannot read document: {path.name}"
            ) from exc

        try:
            content = raw.decode("utf-8", errors="strict")
        except UnicodeDecodeError as exc:
            raise DocumentLoadError(
                f"Invalid UTF-8 document: {path.name}"
            ) from exc

        if not content.strip():
            raise DocumentLoadError(
                f"Document contains no usable text: "
                f"{path.name}"
            )

        checksum = hashlib.sha256(raw).hexdigest()

        return content, checksum, len(raw)

    def iter_documents(self) -> Iterator[Document]:
        self._validate_directory()

        seen_ids = set()
        seen_hashes = set()

        try:
            paths = sorted(
                self.directory.iterdir(),
                key=lambda p: p.name
            )
        except OSError as exc:
            raise DocumentLoadError(
                "Unable to list document directory"
            ) from exc

        for path in paths:
            if path.name in self.ignored_filenames:
                logger.info("document_entry_ignored name=%s", path.name)
                continue
            if path.suffix != ".txt":
                raise DocumentLoadError(f"Unsupported directory entry: {path.name}")

            document_id = self._extract_document_id(
                path.name
            )

            if document_id in seen_ids:
                raise DocumentLoadError(
                    f"Duplicate document ID: {document_id}"
                )

            content, checksum, size = (
                self._read_document(path)
            )

            if checksum in seen_hashes:
                raise DocumentLoadError(
                    f"Duplicate document content: "
                    f"{path.name}"
                )

            seen_ids.add(document_id)
            seen_hashes.add(checksum)

            logger.info(
                "document_loaded id=%s source=%s bytes=%d",
                document_id,
                path.name,
                size,
            )

            yield Document(
                document_id=document_id,
                source=path.name,
                content=content,
                sha256=checksum,
                size_bytes=size,
            )

    def lazy_load(self) -> Iterator[LangChainDocument]:
        """Convert validated fixtures without changing text or source metadata."""
        for document in self.iter_documents():
            yield document.to_langchain()

    def load_documents(self) -> list[dict]:
        documents = [
            {
                "document_id": doc.metadata["document_id"],
                "source": doc.metadata["source"],
                "content": doc.page_content,
                "sha256": doc.metadata["sha256"],
                "size_bytes": doc.metadata["size_bytes"],
            }
            for doc in self.load()
        ]

        logger.info(
            "document_ingestion_completed count=%d",
            len(documents),
        )

        return documents


def load_documents(
    directory: str = str(settings.document_directory),
) -> list[dict]:
    """Backward-compatible document loading interface."""
    loader = DocumentLoader(directory=directory)
    return loader.load_documents()
