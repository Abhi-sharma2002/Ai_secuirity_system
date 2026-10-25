"""Regression tests use temporary files/Chroma and never download a model."""
import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from app.core.config import settings
from app.ingestion.loader import DocumentLoader, DocumentLoadError
from app.ingestion.chunker import chunk_documents
from app.rag import indexer
from app.rag import embeddings, retriever


def document(content='abcdefghij', document_id='D001'):
    return dict(document_id=document_id, source=f'{document_id}.txt', content=content,
                sha256=hashlib.sha256(content.encode()).hexdigest())


def vectors(texts):
    return [[1.0] + [0.0] * (settings.embedding_dimension - 1) for _ in texts]


class LoaderTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def test_valid_order_and_evidence(self):
        for name in ('D002.txt', 'D001.txt'):
            (self.root / name).write_text(name + '\u200b', encoding='utf-8')
        docs = DocumentLoader(str(self.root)).load_documents()
        self.assertEqual([d['document_id'] for d in docs], ['D001', 'D002'])
        self.assertTrue(docs[0]['content'].endswith('\u200b'))

    def test_missing_directory(self):
        with self.assertRaises(DocumentLoadError):
            DocumentLoader(str(self.root / 'missing')).load_documents()

    def test_invalid_inputs(self):
        for name, raw, limit in [('D001.txt', b'', 100), ('D001.txt', b'  ', 100),
                                  ('D001.txt', b'\xff', 100), ('D001.txt', b'ab', 1),
                                  ('bad.txt', b'ok', 100), ('other.csv', b'ok', 100),
                                  ('D\u0660\u0660\u0661.txt', b'ok', 100)]:
            with self.subTest(name=name, raw=raw):
                path = self.root / name
                path.write_bytes(raw)
                with self.assertRaises(DocumentLoadError):
                    DocumentLoader(str(self.root), limit).load_documents()
                path.unlink()

    def test_duplicate_and_symlink(self):
        (self.root / 'D001.txt').write_text('one')
        (self.root / 'D001_other.txt').write_text('two')
        with self.assertRaises(DocumentLoadError):
            DocumentLoader(str(self.root)).load_documents()
        (self.root / 'D001_other.txt').unlink()
        (self.root / 'D002.txt').symlink_to(self.root / 'D001.txt')
        with self.assertRaises(DocumentLoadError):
            DocumentLoader(str(self.root)).load_documents()


class ChunkTests(unittest.TestCase):
    def test_boundaries_unicode_offsets_hashes(self):
        for text, count in [('abc', 1), ('abcde', 1), ('abcdefghij', 3), ('🐍é文' * 4, 4)]:
            chunks = chunk_documents([document(text)], 5, 2)
            self.assertEqual(len(chunks), count)
            self.assertEqual(chunks, chunk_documents([document(text)], 5, 2))
            for c in chunks:
                self.assertEqual(c['content'], text[c['start_char']:c['end_char']])
                self.assertEqual(c['chunk_sha256'], hashlib.sha256(c['content'].encode()).hexdigest())
            for previous, current in zip(chunks, chunks[1:]):
                self.assertEqual(previous['end_char'] - current['start_char'], 2)

    def test_invalid(self):
        for size, overlap in [(0, 0), (5, 5), (True, 0), (5, 1.5)]:
            with self.assertRaises(ValueError):
                chunk_documents([document()], size, overlap)
        with self.assertRaises(ValueError):
            chunk_documents([document('')])
        with self.assertRaises(ValueError):
            chunk_documents([document(), document()])


class EmbeddingTests(unittest.TestCase):
    def test_inputs_and_batch(self):
        self.assertEqual(embeddings.embed_texts([]), [])
        for bad in [[''], [None], 'text']:
            with self.assertRaises(ValueError):
                embeddings.embed_texts(bad)
        model = Mock()
        model.encode.return_value.tolist.return_value = vectors(['a', 'b'])
        with patch.object(embeddings, 'get_embedding_model', return_value=model):
            self.assertEqual(len(embeddings.embed_texts(['a', 'b'])), 2)
        self.assertEqual(model.encode.call_args.kwargs['batch_size'], settings.batch_size)

    def test_invalid_vectors(self):
        for bad in [[], [[1]], [[0.] * settings.embedding_dimension],
                    [[float('nan')] * settings.embedding_dimension],
                    [[float('inf')] * settings.embedding_dimension]]:
            with self.assertRaises(RuntimeError):
                embeddings.validate_vectors(bad, 1)

    def test_cached_initialization(self):
        import sys
        fake = Mock()
        embeddings.get_embedding_model.cache_clear()
        self.addCleanup(embeddings.get_embedding_model.cache_clear)
        with patch.dict(sys.modules, {'sentence_transformers': fake}):
            self.assertIs(embeddings.get_embedding_model(), embeddings.get_embedding_model())
        fake.SentenceTransformer.assert_called_once()


class IndexRetrievalTests(unittest.TestCase):
    def setUp(self):
        import chromadb
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.client = chromadb.PersistentClient(path=self.temp.name)
        self.client_patch = patch.object(indexer, 'get_client', return_value=self.client)
        self.client_patch.start()
        self.addCleanup(self.client_patch.stop)
        self.embed_patch = patch.object(indexer, 'embed_texts', side_effect=vectors)
        self.embed = self.embed_patch.start()
        self.addCleanup(self.embed_patch.stop)
        self.chunks = chunk_documents([document(), document('other text', 'D002')], 5, 2)

    def test_repeat_and_configuration_versions(self):
        result = indexer.index_chunks(self.chunks)
        self.embed.reset_mock()
        self.assertEqual(result, indexer.index_chunks(self.chunks))
        self.embed.assert_not_called()
        changed = chunk_documents([document('different')], 5, 2)
        self.assertNotEqual(result['collection'], indexer.index_chunks(changed)['collection'])
        with patch.object(indexer, 'index_configuration', return_value={'embedding_model': 'other'}):
            self.assertNotEqual(result['dataset_version'], indexer.calculate_dataset_version(self.chunks))
        with self.assertRaises(ValueError):
            indexer.index_chunks(self.chunks + self.chunks)

    def test_interruption_resume_and_integrity(self):
        with patch.object(indexer, 'BATCH_SIZE', 1), patch.object(indexer, 'embed_texts', side_effect=[vectors(['a']), RuntimeError('interrupted')]):
            with self.assertRaises(RuntimeError):
                indexer.index_chunks(self.chunks)
        name = 'enterprise_documents_' + indexer.calculate_dataset_version(self.chunks)
        collection = self.client.get_collection(name)
        self.assertEqual(collection.metadata['status'], 'building')
        with patch.object(retriever, 'get_client', return_value=self.client):
            with self.assertRaises(RuntimeError):
                retriever.DocumentRetriever(name)
        indexer.index_chunks(self.chunks)
        collection.update(ids=[self.chunks[0]['chunk_id']], documents=['tampered'], embeddings=vectors(['tampered']))
        with self.assertRaises(RuntimeError):
            indexer.index_chunks(self.chunks)

    def test_incompatible_and_empty_collections(self):
        result = indexer.index_chunks(self.chunks)
        collection = self.client.get_collection(result['collection'])
        metadata = dict(collection.metadata)
        metadata['embedding_model'] = 'incompatible-model'
        collection.modify(metadata=metadata)
        with self.assertRaises(RuntimeError):
            indexer.index_chunks(self.chunks)
        name = 'enterprise_documents_0000000000000000'
        self.client.create_collection(name, metadata={**indexer.index_configuration(),
            'dataset_version': '0000000000000000', 'expected_chunks': 1, 'status': 'verified'})
        with patch.object(retriever, 'get_client', return_value=self.client):
            for collection_name in (name, result['collection']):
                with self.assertRaises(RuntimeError):
                    retriever.DocumentRetriever(collection_name)

    def test_retrieval(self):
        name = indexer.index_chunks(self.chunks)['collection']
        with patch.object(retriever, 'get_client', return_value=self.client), patch.object(retriever, 'embed_texts', side_effect=vectors):
            search = retriever.DocumentRetriever(name)
            hits = search.search('question', {'D001'})
            self.assertTrue(hits)
            self.assertTrue(all(h.document_id == 'D001' for h in hits))
            self.assertEqual(search.search('question', {'D099'}), [])
            for question in ['', None, 1]:
                with self.assertRaises(ValueError):
                    search.search(question, {'D001'})
            for k in [0, 21, True, 1.5]:
                with self.assertRaises(ValueError):
                    search.search('question', {'D001'}, k)
            with self.assertRaises(PermissionError):
                search.search('question', set())
            for result in [dict(ids=[['x']], documents=[['text']], metadatas=[[{}]], distances=[[0.]]),
                           dict(ids=[['x']], documents=[[]], metadatas=[[]], distances=[[]])]:
                with patch.object(search.collection, 'query', return_value=result):
                    with self.assertRaises(RuntimeError):
                        search.search('question', {'D001'})
            chunk = self.chunks[0]
            for distance in [float('nan'), float('inf'), -1., 3.]:
                response = dict(ids=[[chunk['chunk_id']]], documents=[[chunk['content']]],
                                metadatas=[[indexer.chunk_metadata(chunk)]], distances=[[distance]])
                with patch.object(search.collection, 'query', return_value=response):
                    with self.assertRaises(RuntimeError):
                        search.search('question', {'D001'})
            with self.assertRaises(indexer.chromadb.errors.NotFoundError):
                retriever.DocumentRetriever('enterprise_documents_0000000000000000')


if __name__ == '__main__':
    unittest.main()
