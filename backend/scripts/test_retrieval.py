
import os

from app.rag.pipeline import build_retrieval_pipeline


COLLECTION = os.environ["RAG_COLLECTION"]


def main():
    retriever = build_retrieval_pipeline(COLLECTION, {"D001"}, top_k=3)

    question = "What is the employee leave policy?"

    results = retriever.invoke(question)

    assert results, "No results returned"

    for hit in results:
        assert hit.metadata['document_id'] == "D001"

        print(f"Chunk: {hit.id}")
        print(f"Document: {hit.metadata['document_id']}")
        print(f"Distance: {hit.metadata['distance']:.4f}")
        print(f"Source: {hit.metadata['source']}")
        print(f"Text: {hit.page_content[:250]}")
        print("-" * 60)

    print("PASS: Authorized retrieval completed")


if __name__ == "__main__":
    main()
