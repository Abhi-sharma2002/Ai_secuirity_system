
import logging

from app.core.logging import configure_logging
from app.ingestion.loader import DocumentLoader
from app.ingestion.pipeline import build_ingestion_pipeline


configure_logging()

logger = logging.getLogger(__name__)


def main():
    logger.info("Starting enterprise document ingestion")

    documents = DocumentLoader().load()

    result = build_ingestion_pipeline().invoke(documents)
    logger.info("Ingested documents=%d chunks=%d", len(documents), result["indexed_chunks"])

    logger.info("Collection: %s", result["collection"])
    logger.info("Dataset version: %s", result["dataset_version"])
    logger.info("Indexed chunks: %d", result["indexed_chunks"])
    logger.info("Status: %s", result["status"])

    print("\nPASS: Document ingestion completed successfully")


if __name__ == "__main__":
    main()
