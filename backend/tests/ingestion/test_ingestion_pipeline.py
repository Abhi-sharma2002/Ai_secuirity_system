"""Native LangChain ingestion keeps legacy index identity and integrity checks."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import chromadb
from langchain_core.documents import Document
from langchain_core.runnables import RunnableSequence

from app.core.config import settings
from app.ingestion.loader import DocumentLoader
from app.ingestion.chunker import chunk_documents, split_documents
from app.rag.indexer import chunk_records, index_chunks, index_documents
from app.ingestion.pipeline import build_ingestion_pipeline
from app.rag.pipeline import build_retrieval_pipeline


class IngestionPipelineTests(unittest.TestCase):
    def test_native_pipeline_matches_legacy_and_retrieves(self):
        client = chromadb.EphemeralClient()
        vectors = lambda texts: [[1.0] + [0.0] * (settings.embedding_dimension - 1) for _ in texts]
        with tempfile.TemporaryDirectory() as directory:
            Path(directory, 'D001_policy.txt').write_bytes(b'Leave policy: twelve days.\r\n')
            loader = DocumentLoader(directory)
            native = loader.load()
            legacy = loader.load_documents()
            self.assertEqual(chunk_documents(native, 12, 3), chunk_documents(legacy, 12, 3))
            self.assertEqual(chunk_records(split_documents(native, 12, 3)), chunk_documents(legacy, 12, 3))
            with patch('app.rag.indexer.get_client', return_value=client), \
                 patch('app.rag.retriever.get_client', return_value=client), \
                 patch('app.rag.indexer.embed_texts', side_effect=vectors), \
                 patch('app.rag.retriever.embed_texts', side_effect=vectors):
                pipeline = build_ingestion_pipeline(12, 3)
                self.assertIsInstance(pipeline, RunnableSequence)
                result = pipeline.invoke(native)
                self.assertEqual(result, index_chunks(chunk_documents(legacy, 12, 3)))
                self.assertEqual(result, pipeline.invoke(native))
                evidence = build_retrieval_pipeline(result['collection'], {'D001'}).invoke('leave?')
                self.assertTrue(evidence)
                for document in evidence:
                    self.assertIsInstance(document, Document)
                    self.assertEqual(document.metadata['document_id'], 'D001')
                    start, end = document.metadata['start_char'], document.metadata['end_char']
                    self.assertEqual(document.page_content, native[0].page_content[start:end])

    def test_native_documents_do_not_bypass_checks(self):
        source = Document(id='D001', page_content='policy', metadata={
            'document_id': 'D001', 'source': 'D001.txt', 'sha256': '0'*64})
        with self.assertRaisesRegex(ValueError, 'checksum'):
            split_documents([source])
        source.id = 'D002'
        with self.assertRaisesRegex(ValueError, 'ID differs'):
            split_documents([source])
        chunk = Document(id='chunk-a', page_content='policy', metadata={'chunk_id': 'chunk-b'})
        with self.assertRaisesRegex(ValueError, 'ID differs'):
            index_documents([chunk])
        chunk.id = 'chunk-b'
        chunk.metadata['content'] = 'replacement'
        with self.assertRaisesRegex(ValueError, 'page_content'):
            index_documents([chunk])
        with self.assertRaises(ValueError):
            split_documents([{'content': 'policy'}])

    def test_invalid_pipeline_configuration(self):
        for size, overlap in [(0, 0), (5, 5), (True, 0), (10, 1.5)]:
            with self.assertRaises(ValueError):
                build_ingestion_pipeline(size, overlap)
