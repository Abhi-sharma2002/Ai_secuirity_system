"""Real local Chroma storage, synthetic fixture and embeddings; no provider traffic."""
from contextlib import ExitStack
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import chromadb

from app.core.config import settings
from app.evaluation import simple_index as index
from app.evaluation.simple_config import EvaluationError, load_config
from app.ingestion.parsers import _extract


class LocalEvaluationIndexTests(unittest.TestCase):
    def setUp(self):
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.root = Path(self.stack.enter_context(tempfile.TemporaryDirectory()))
        self.dataset = self.root / 'backend/benchmark_v3'
        (self.dataset / 'documents').mkdir(parents=True)
        raw = b'Synthetic leave policy. ' * 60
        self.source = self.dataset / 'documents/policy.txt'
        self.source.write_bytes(raw)
        self.data = {'fixtures': [{'fixture_id': 'policy', 'path': 'documents/policy.txt',
                                  'sha256': hashlib.sha256(raw).hexdigest()}]}
        (self.dataset / 'manifest.json').write_text(json.dumps(self.data))
        self.config = load_config()
        self.store = self.root / '.cache/eval'
        self.stack.enter_context(patch.object(index, 'ROOT', self.root))
        self.stack.enter_context(patch('huggingface_hub.constants.HF_HUB_OFFLINE', True))
        self.stack.enter_context(patch.dict(os.environ, {'TRANSFORMERS_OFFLINE': '1'}))
        self.stack.enter_context(patch('app.ingestion.parsers.parse', side_effect=_extract))
        self.stack.enter_context(patch('socket.socket.connect', side_effect=AssertionError('Network forbidden')))
        vector = [1.0] + [0.0] * (settings.embedding_dimension - 1)
        self.embed = self.stack.enter_context(patch('app.rag.embeddings.ProjectEmbeddings.embed_documents',
                                                   side_effect=lambda texts: [vector[:] for _ in texts]))

    def prepare(self):
        return index.prepare_store(self.data, self.config, self.store)

    def test_fresh_index_provenance_and_rebuild_preserves_previous_generation(self):
        first = self.prepare()
        previous_identity = (self.store / 'identity.json').read_bytes()
        identity = json.loads(previous_identity)
        collection = chromadb.PersistentClient(path=str(index.collection_path(self.store, identity)),
            settings=chromadb.Settings(anonymized_telemetry=False)).get_collection('benchmark_v3')
        saved = collection.get(include=['documents', 'metadatas'])
        self.assertEqual(collection.count(), first['n_chunks'])
        self.assertEqual(first['n_documents'], 1)
        self.assertEqual(first['provider_requests_made'], 0)
        self.assertGreater(first['n_chunks'], 1)
        for meta in saved['metadatas']:
            self.assertEqual(meta['fixture_sha256'], self.data['fixtures'][0]['sha256'])
            self.assertEqual(meta['chunk_size'], self.config['chunk_size'])
            self.assertEqual(meta['chunk_overlap'], self.config['chunk_overlap'])
            self.assertFalse({'expected_keywords', 'canary', 'expected_evidence'} & set(meta))
        second = self.prepare()
        self.assertNotEqual(first['generation'], second['generation'])
        archived = list((self.root / 'archive/local_evaluation_stores').glob('*/identity.json'))
        self.assertEqual(len(archived), 1)
        self.assertEqual(archived[0].read_bytes(), previous_identity)
        self.assertTrue((archived[0].parent / 'chroma' / first['generation'] / 'chroma.sqlite3').exists())
        self.assertFalse(index.collection_path(self.store, identity).exists())
        self.assertEqual(collection.get(include=['documents', 'metadatas']), saved)

    def test_changed_fixture_refuses_activation_and_preserves_identity(self):
        self.prepare()
        original = (self.store / 'identity.json').read_bytes()
        self.source.write_bytes(b'Changed fixture')
        with self.assertRaisesRegex(EvaluationError, 'Fixture changed'):
            self.prepare()
        self.assertEqual((self.store / 'identity.json').read_bytes(), original)
        self.assertFalse((self.root / 'archive').exists())

    def test_generation_cannot_escape_local_store(self):
        for generation in ('../other', '', '/tmp', 'a/b'):
            with self.subTest(generation=generation), self.assertRaises(EvaluationError):
                index.collection_path(self.store, {'generation': generation})

    def test_preparation_refuses_nonoffline_embeddings_before_ingestion(self):
        with patch('huggingface_hub.constants.HF_HUB_OFFLINE', False), self.assertRaisesRegex(EvaluationError, 'downloads are disabled'):
            self.prepare()
        self.embed.assert_not_called()
        self.assertFalse(self.store.exists())


if __name__ == '__main__':
    unittest.main()
