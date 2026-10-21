
import logging

from app.ingestion.loader import DocumentLoader


def main():
    documents = DocumentLoader().load()

    print(f"Total documents loaded: {len(documents)}")

    for document in documents:
        print(
            f"ID: {document.metadata['document_id']} | "
            f"Source: {document.metadata['source']} | "
            f"SHA256: {document.metadata['sha256']}"
        )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
