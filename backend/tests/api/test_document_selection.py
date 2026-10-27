"""User-chosen evidence scope, with no model calls or production storage."""
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch
from fastapi import HTTPException
from app.api import runtime
from app.storage import registry


class SelectionTests(TestCase):
    def setUp(self):
        self.tmp=TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        p=patch.object(registry,'ROOT',Path(self.tmp.name));p.start();self.addCleanup(p.stop)
        registry.initialize()
        self.items=[{'document_id':'one','id':'v1'}, {'document_id':'two','id':'v2'}]
        p=patch.object(runtime.life,'snapshot',return_value=self.items);p.start();self.addCleanup(p.stop)

    def test_search_and_answer_use_only_the_selected_document(self):
        q=runtime.Query(question='A benign policy question',request_id='scoped-request',document_id='two')
        with patch.object(runtime.retrieval,'search',return_value={'hits':[]}) as search:
            runtime.search(q);search.assert_called_once_with(q.question,[self.items[1]])
        with patch.object(runtime,'respond',return_value={'status':'answered'}) as answer:
            runtime.chat(q);runtime.chat(q)
            self.assertEqual(answer.call_count,1)
            self.assertEqual(answer.call_args.kwargs['snapshot_items'],[self.items[1]])
            with self.assertRaises(HTTPException): runtime.chat(q.model_copy(update={'document_id':'one'}))

    def test_missing_document_never_submits(self):
        q=runtime.Query(question='A benign policy question',request_id='missing-request',document_id='gone')
        with patch.object(runtime,'respond') as answer:
            with self.assertRaises(HTTPException):runtime.chat(q)
            answer.assert_not_called()
        with registry.connect() as db:self.assertEqual(db.execute('SELECT count(*) FROM requests').fetchone()[0],0)

    def test_comparison_gets_the_same_selected_scope(self):
        q=runtime.Query(question='A benign policy question',request_id='compare-request',document_id='one')
        with patch('app.rag.comparison.compare',return_value={'status':'completed'}) as compare:
            runtime.compare_query(q)
            self.assertEqual(compare.call_args.kwargs['snapshot_items'],[self.items[0]])

    def test_unscoped_fingerprint_preserves_old_request_identity(self):
        q=runtime.Query(question='A benign policy question',request_id='legacy-request')
        self.assertEqual(runtime.query_fingerprint(q),q.model_dump_json(exclude={'request_id','document_id'}))
