"""Optional full dataset integration using cached CPU model and temporary storage."""
import os
import tempfile
import unittest
from unittest.mock import patch

from app.ingestion.loader import load_documents
from app.ingestion.chunker import chunk_documents
from app.rag import indexer
from app.rag import retriever


@unittest.skipUnless(os.getenv('RUN_MODEL_TESTS') == '1', 'Set RUN_MODEL_TESTS=1 for real CPU model test')
class LiveRagTests(unittest.TestCase):
    def test_dataset_round_trip(self):
        import chromadb
        with tempfile.TemporaryDirectory() as directory:
            client = chromadb.PersistentClient(path=directory)
            with patch.object(indexer, 'get_client', return_value=client), patch.object(retriever, 'get_client', return_value=client):
                chunks = chunk_documents(load_documents())
                result = indexer.index_chunks(chunks)
                with patch.object(indexer, 'embed_texts', side_effect=AssertionError('Unexpected re-embedding')):
                    self.assertEqual(indexer.index_chunks(chunks), result)
                search = retriever.DocumentRetriever(result['collection'])
                hits = search.search('What is the employee leave policy?', {'D001'}, 3)
                self.assertTrue(hits)
                self.assertTrue(all(hit.document_id == 'D001' for hit in hits))
                originals = {chunk['chunk_id']: chunk for chunk in chunks}
                for hit in hits:
                    self.assertEqual(hit.content, originals[hit.chunk_id]['content'])
                    self.assertEqual(hit.chunk_sha256, originals[hit.chunk_id]['chunk_sha256'])
