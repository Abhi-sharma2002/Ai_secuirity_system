
from collections import Counter

from app.ingestion.loader import load_documents
from app.ingestion.chunker import chunk_documents


def main():
    documents = load_documents()
    chunks = chunk_documents(
        documents,
        chunk_size=1000,
        chunk_overlap=150,
    )

    print("Documents:", len(documents))
    print("Total chunks:", len(chunks))

    counts = Counter(c["document_id"] for c in chunks)

    for doc_id in sorted(counts):
        print(f"{doc_id}: {counts[doc_id]} chunks")

    assert documents
    assert len(counts) == len(documents)

    assert len({c["chunk_id"] for c in chunks}) == len(chunks)

    for chunk in chunks:
        original = next(
            d for d in documents
            if d["document_id"] == chunk["document_id"]
        )

        assert chunk["content"] == original["content"][
            chunk["start_char"]:chunk["end_char"]
        ]

        assert len(chunk["content"]) <= 1000

    print("\nPASS: Chunking and source offsets validated")

    print("\nExample chunk metadata:")
    example = chunks[0]

    for key, value in example.items():
        if key != "content":
            print(f"{key}: {value}")

    print("\nFirst 250 characters:")
    print(example["content"][:250])


if __name__ == "__main__":
    main()
