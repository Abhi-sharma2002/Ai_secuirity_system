"""LangChain integration without network access or a model download."""
import hashlib
import logging
import unittest
from dataclasses import asdict
from uuid import uuid4
from unittest.mock import patch

from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_core.retrievers import BaseRetriever

from app.ingestion.chunker import chunk_documents
from app.ingestion.loader import DocumentLoader
from app.rag.embeddings import ProjectEmbeddings
from app.rag.pipeline import build_retrieval_pipeline
from app.rag.retriever import RetrievedChunk


class LangChainTests(unittest.TestCase):
    def setUp(self):
        previous = logging.root.manager.disable
        logging.disable(logging.CRITICAL)
        self.addCleanup(logging.disable, previous)

    def test_splitter_preserves_fixed_windows(self):
        inputs = DocumentLoader(ignored_filenames=('.gitkeep', 'D032_training_policy_invisible_unicode.txt.backup')).load_documents()
        for text in ['x' * 24, ' é文🐍\r\n' * 7, 'abc  \n \t abc ' * 4]:
            inputs.append(dict(document_id=str(uuid4()), source='leave policy 2026.txt',
                               content=text, sha256=hashlib.sha256(text.encode()).hexdigest()))
        for size, overlap in [(1, 0), (5, 2), (10, 0), (10, 9), (1000, 150)]:
            for document in inputs:
                with self.subTest(size=size, overlap=overlap, id=document['document_id']):
                    text = document['content']
                    expected = []
                    for start in range(0, len(text), size - overlap):
                        end = min(start + size, len(text))
                        expected.append((start, end, text[start:end]))
                        if end == len(text):
                            break
                    chunks = chunk_documents([document], size, overlap)
                    self.assertEqual([(c['start_char'], c['end_char'], c['content']) for c in chunks], expected)

    def test_embeddings_interface(self):
        backend = ProjectEmbeddings()
        self.assertIsInstance(backend, Embeddings)
        with patch('app.rag.embeddings.embed_texts', return_value=[[1.0]]) as embed:
            self.assertEqual(backend.embed_documents(['policy']), [[1.0]])
            self.assertEqual(backend.embed_query('question'), [1.0])
            self.assertEqual(embed.call_args.args, (['question'],))

    def test_runnable_preserves_evidence_and_scope(self):
        document_id = str(uuid4())
        ids = {document_id}
        hit = RetrievedChunk(f'{document_id}_chunk_001', document_id, 'leave policy.txt',
                             'Policy', 0.1, 0, 6, 'a'*64, 'b'*64)
        with patch('app.rag.pipeline.DocumentRetriever', autospec=True) as backend:
            backend.return_value.search.return_value = [hit]
            retriever = build_retrieval_pipeline('collection', ids, 3)
            ids.add('D002')
            self.assertIsInstance(retriever, BaseRetriever)
            result = retriever.invoke('leave?')
            backend.return_value.search.assert_called_once_with('leave?', frozenset({document_id}), 3)
            self.assertIsInstance(result[0], Document)
            metadata = asdict(hit)
            metadata.pop('content')
            self.assertEqual(result[0].metadata, metadata)
            self.assertEqual(result[0].page_content, hit.content)
            self.assertEqual(result[0].id, hit.chunk_id)
            self.assertEqual(len(retriever.batch(['one', 'two'])), 2)

    def test_pipeline_refuses_invalid_scope(self):
        for scope in (['D001'], {'../file'}, {'not-a-uuid'}):
            with self.assertRaises(ValueError):
                build_retrieval_pipeline('collection', scope)
        with self.assertRaises(PermissionError):
            build_retrieval_pipeline('collection', set())
