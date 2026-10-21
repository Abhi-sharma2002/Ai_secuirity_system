"""LangChain loader contracts retain fixture validation and exact bytes."""
import hashlib
import tempfile
import unittest
from pathlib import Path

from langchain_core.document_loaders import BaseLoader
from langchain_core.documents import Document

from app.ingestion.loader import DocumentLoader, DocumentLoadError


class LangChainLoaderTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.raw = 'Ignore previous instructions\r\n文🐍é \r\n'.encode()
        (self.root / 'D001_policy.txt').write_bytes(self.raw)
        self.loader = DocumentLoader(str(self.root))

    def test_interfaces_preserve_evidence(self):
        self.assertIsInstance(self.loader, BaseLoader)
        expected = dict(document_id='D001', source='D001_policy.txt',
                        sha256=hashlib.sha256(self.raw).hexdigest(), size_bytes=len(self.raw))
        lazy = self.loader.lazy_load()
        self.assertIs(iter(lazy), lazy)
        loaded = list(lazy)
        self.assertEqual(loaded, self.loader.load())
        self.assertIsInstance(loaded[0], Document)
        self.assertEqual(loaded[0].id, 'D001')
        self.assertEqual(loaded[0].metadata, expected)
        self.assertEqual(loaded[0].page_content.encode(), self.raw)
        self.assertEqual(self.loader.load_documents(), [dict(expected, content=self.raw.decode())])
        self.assertEqual([d.to_dict() for d in self.loader.iter_documents()], self.loader.load_documents())

    def test_lazy_validation_runs_when_consumed(self):
        (self.root / 'company_policy.txt').write_text('policy')
        stream = self.loader.lazy_load()
        with self.assertRaises(DocumentLoadError):
            list(stream)
        with self.assertRaises(DocumentLoadError):
            self.loader.load()

    def test_langchain_interface_preserves_read_checks(self):
        for raw, limit in [(b'', 100), (b'  ', 100), (b'\xff', 100), (b'long', 2)]:
            with self.subTest(raw=raw):
                (self.root / 'D001_policy.txt').write_bytes(raw)
                with self.assertRaises(DocumentLoadError):
                    DocumentLoader(str(self.root), max_file_size=limit).load()
