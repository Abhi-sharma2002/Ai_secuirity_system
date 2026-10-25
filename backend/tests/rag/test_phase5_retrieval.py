"""Phase 5 focused assembly/maintenance checks, explicit retrieval/vector/LLM doubles.
Real CPU fresh-process persistence is separately audited by scripts.audit_phase5.
"""
from app.rag import retrieval
import contextlib
import hashlib
import io
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from uuid import uuid4

from app.storage import registry as reg
from app.core.config import settings
from app.ingestion import lifecycle as life, maintenance
from app.rag import indexer
from app.rag import assistant
from app.rag.retriever import RetrievedChunk


class ContextBudgetTests(unittest.TestCase):
    def setUp(self):
        guard = patch('socket.socket.connect', side_effect=AssertionError('Network forbidden'))
        guard.start(); self.addCleanup(guard.stop)
        self.assertEqual(settings.top_k, 5)

    def assemble(self, texts, distances=None, ids=None):
        item = {'id': 'version-test', 'document_id': str(uuid4()), 'filename': 'Unicode नीति.md',
                'sha256': 'a' * 64, 'index_name': 'test-boundary-collection', 'partial_accepted': True}
        ids = ids or [f'chunk-{i}' for i in range(len(texts))]
        rows = [RetrievedChunk(cid, item['document_id'], item['filename'], text,
                               distances[i] if distances else i / 10, 0, len(text),
                               item['sha256'], hashlib.sha256(text.encode()).hexdigest())
                for i, (cid, text) in enumerate(zip(ids, texts))]
        class Collection:
            def get(self, ids, include):
                return {'ids': ids, 'metadatas': [{'page': i+1, 'section': f'page {i+1}'} for i in range(len(ids))]}
        client = SimpleNamespace(get_collection=lambda *a, **kw: Collection())
        with patch('app.rag.retriever.DocumentRetriever') as retriever, patch.object(indexer, 'get_client', return_value=client):
            retriever.return_value.search.return_value = rows
            result = retrieval.search('Question?', [item])
            retriever.return_value.search.assert_called_once_with('Question?', {item['document_id']}, settings.top_k)
        for hit in result['hits']:
            self.assertEqual((hit['document_id'], hit['version_id'], hit['sha256'], hit['filename']),
                             (item['document_id'], item['id'], item['sha256'], item['filename']))
            self.assertEqual(hit['text'], texts[ids.index(hit['id'])])
            self.assertTrue(hit['partial_text'])
            hit['text'].encode().decode('utf-8')
        self.assertEqual(len(result['hits']) + len(result['omitted_ids']), len(rows))
        return result

    def test_below_exact_over_multibyte_whole_chunk_budget(self):
        for last, expected in [('🙂' * 999 + '漢', 11999), ('🙂' * 1000, 12000)]:
            with self.subTest(bytes=expected):
                texts = ['🙂' * 1000, '🙂' * 1000, last]
                result = self.assemble(texts)
                self.assertEqual(sum(len(h['text'].encode()) for h in result['hits']), expected)
                self.assertEqual([h['text'] for h in result['hits']], texts)
                self.assertEqual(result['omitted_ids'], [])
        # 8000 + 3999 fits; the next two-byte candidate does not; later one byte fits.
        texts = ['🙂' * 1000, '🙂' * 1000, '🙂' * 999 + '漢', 'é', 'x']
        result = self.assemble(texts)
        self.assertEqual([h['id'] for h in result['hits']], ['chunk-0', 'chunk-1', 'chunk-2', 'chunk-4'])
        self.assertEqual(result['omitted_ids'], ['chunk-3'])
        self.assertEqual(sum(len(h['text'].encode()) for h in result['hits']), 12000)
        exact = self.assemble(['🙂' * 1000] * 3 + ['é'])
        self.assertEqual(exact['omitted_ids'], ['chunk-3'])
        # Labels/JSON separators exceed the source-text budget by design.
        self.assertGreater(len(assistant.messages('B', 'Question?', result['hits'])[-1]['content'].encode()), 12000)

    def test_determinism_tie_order_topk_oversized_and_empty(self):
        first = self.assemble(['é', '文', '🙂'], distances=[0.1]*3, ids=['z', 'a', 'm'])
        second = self.assemble(['é', '文', '🙂'], distances=[0.1]*3, ids=['z', 'a', 'm'])
        self.assertEqual([h['id'] for h in first['hits']], ['a', 'm', 'z'])
        self.assertEqual([h['id'] for h in first['hits']], [h['id'] for h in second['hits']])
        result = self.assemble(['é'] * 6)
        self.assertEqual(len(result['hits']), settings.top_k)
        self.assertEqual(result['omitted_ids'], ['chunk-5'])
        # Synthetic oversized candidate is impossible with current 1000-char chunks;
        # this explicitly tests the assembly boundary without altering chunk settings.
        result = self.assemble(['🙂' * 3000 + 'x', 'usable'])
        self.assertEqual([h['id'] for h in result['hits']], ['chunk-1'])
        self.assertEqual(result['omitted_ids'], ['chunk-0'])
        for texts in ([], ['🙂' * 3000 + 'x']):
            result = self.assemble(texts)
            self.assertEqual(result['hits'], [])
            with patch.object(assistant.live, 'reserve', side_effect=AssertionError('No reservation expected')):
                for mode in ('A', 'B'):
                    response = assistant.respond('Question?', mode, initial=result)
                    self.assertEqual(response['status'], 'insufficient_evidence')
                    self.assertEqual(response['supplied_evidence'], [])
                    self.assertEqual(response['references'], [])

    def test_assembled_vs_supplied_and_references_with_explicit_llm_doubles(self):
        retrieval = self.assemble(['Fact one', 'Fact two', '🙂' * 3000 + 'x'])
        for mode in ('A', 'B', 'C'):
            with self.subTest(mode=mode):
                selected = retrieval['hits'][1:] if mode == 'C' else retrieval['hits']
                def call(messages, schema, stage, reservation):
                    payload = json.loads(messages[-1]['content'])
                    if stage == 'screening':
                        self.assertEqual(payload['sources'], retrieval['hits'])
                        return json.dumps({'question_flagged': False, 'flagged_source_ids': ['chunk-0'],
                                           'reason_codes': ['instruction_redirection']}), {'stage': stage}
                    self.assertEqual(payload['sources'], selected)
                    return json.dumps({'status': 'answered', 'answer': 'EXPLICIT TEST DOUBLE',
                                       'source_ids': [h['id'] for h in selected]}), {'stage': stage}
                with patch.object(assistant.live, 'reserve', return_value=['TEST-S', 'TEST-G']), \
                     patch.object(assistant.live, 'call', side_effect=call):
                    result = assistant.respond('Question?', mode, initial=retrieval)
                self.assertEqual(result['status'], 'answered')
                self.assertEqual(result['candidate_evidence'], retrieval['hits'])
                self.assertEqual(result['supplied_evidence'], selected)
                self.assertEqual(result['references'], selected)
                self.assertEqual(result['omitted_ids'], ['chunk-2'])


class MaintenanceFailureTests(unittest.TestCase):
    def test_parser_mismatch_and_failed_rebuild_preserve_active_pointer(self):
        import chromadb
        from starlette.datastructures import UploadFile
        with tempfile.TemporaryDirectory(prefix='phase5-unit-') as folder:
            root = Path(folder).resolve()
            runtime, vectors = root/'runtime', root/'chroma'
            assert runtime.is_relative_to(root) and vectors.is_relative_to(root)
            client = chromadb.PersistentClient(path=str(vectors), settings=chromadb.Settings(anonymized_telemetry=False))
            with patch.object(reg, 'ROOT', runtime), patch.object(indexer, 'get_client', return_value=client), \
                 patch.object(indexer, 'embed_texts', side_effect=lambda texts: [[1.]+[0.]*(settings.embedding_dimension-1) for _ in texts]), \
                 patch('socket.socket.connect', side_effect=AssertionError('Network forbidden')):
                reg.initialize()
                f = UploadFile(io.BytesIO(b'Actual parser; embedding vectors are TEST DOUBLES.'), filename='ordinary.txt')
                try:
                    item = life.ingest(f)
                finally:
                    f.file.close()
                self.assertEqual(item['status'], 'ready')
                def inventory():
                    with reg.connect() as db:
                        return {t: [tuple(r) for r in db.execute('SELECT * FROM '+t+' ORDER BY id')] for t in ('documents','versions')}
                def apply():
                    # Every mutable path is checked before each disposable apply.
                    self.assertTrue(reg.ROOT.resolve().is_relative_to(root))
                    self.assertTrue(vectors.resolve().is_relative_to(root))
                    with patch('sys.argv', ['maintenance', 'rebuild', '--apply']), contextlib.redirect_stdout(io.StringIO()):
                        maintenance.main()
                before = inventory()
                with patch.object(maintenance, 'PARSER_VERSION', 'TEST-MISMATCH'), self.assertRaisesRegex(ValueError, 'Parser fingerprint changed'):
                    apply()
                self.assertEqual(inventory(), before)
                with patch.object(indexer, 'index_documents', side_effect=RuntimeError('EXPLICIT failed index double')), self.assertRaises(RuntimeError):
                    apply()
                self.assertEqual(inventory(), before)
                apply()
                self.assertEqual(inventory(), before)
                self.assertEqual([x['id'] for x in life.snapshot()], [item['id']])


if __name__ == '__main__':
    unittest.main()
