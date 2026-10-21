"""Real temporary raw/SQLite/Chroma accounting; deterministic embedding doubles only.

Reuse existing lifecycle setup/ingest helpers. No provider calls/model downloads.
"""
import contextlib
import io
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
import unittest
from unittest.mock import patch

from app.core import registry as reg
from app.ingestion import lifecycle as life, maintenance
from app.main import app
from fastapi.testclient import TestClient
import test_runtime_v2 as runtime_tests


class StorageLifecycleTests(unittest.TestCase):
    setUp = runtime_tests.LifecycleV2Tests.setUp
    patch = runtime_tests.LifecycleV2Tests.patch
    ingest = runtime_tests.LifecycleV2Tests.ingest

    def stored(self):
        folder = reg.ROOT/'raw'
        return {p.name:p.read_bytes() for p in folder.glob('*')}

    def size(self):
        return sum(map(len, self.stored().values()))

    def inventory(self):
        with reg.connect() as db:
            return tuple(tuple(tuple(row) for row in db.execute('SELECT * FROM '+table+' ORDER BY id'))
                         for table in ('documents','versions'))

    def full(self, limit):
        self.patch('app.ingestion.lifecycle.MAX_STORAGE',limit)

    def exceeds(self, raw, did=None, expected=None):
        before, inventory = self.stored(), self.inventory()
        with self.assertRaisesRegex(life.LifecycleError,'Storage limit reached') as caught:
            self.ingest(raw=raw,did=did,expected=expected)
        self.assertEqual(caught.exception.code,413)
        self.assertEqual(self.stored(),before)
        self.assertEqual(self.inventory(),inventory)  # No phantom version or reservation.

    def assert_usable(self, item):
        hits=life.search('policy')['hits']
        self.assertTrue(any(h['version_id']==item['id'] for h in hits))
        self.assertTrue(all(h['version_id'] in {i['id'] for i in life.snapshot()} for h in hits))

    def cleanup(self, apply=False):
        # Actual maintenance algorithm and real disposable index. No production collections touched.
        args=['maintenance','cleanup']+(['--apply'] if apply else [])
        with patch('sys.argv',args), contextlib.redirect_stdout(io.StringIO()) as out:
            maintenance.main()
        return out.getvalue()

    def test_below_exact_and_one_byte_over_total_boundary(self):
        self.full(10)
        first=self.ingest(raw=b'a'*9)
        self.assertEqual(first['status'],'ready'); self.assertEqual(self.size(),9)
        second=self.ingest(raw=b'b')
        self.assertEqual(second['status'],'ready'); self.assertEqual(self.size(),10)
        self.exceeds(b'c')
        self.assertEqual(len(life.snapshot()),2)
        self.assert_usable(first); self.assert_usable(second)

    def test_individually_valid_but_cumulatively_over_limit(self):
        self.full(10)
        first=self.ingest(raw=b'a'*6)
        self.exceeds(b'b'*5)
        self.assertEqual(self.size(),6); self.assert_usable(first)

    def test_dedup_at_capacity_same_name_changed_content_and_scope(self):
        self.full(10)
        first=self.ingest(raw=b'a'*10)
        before=self.inventory()
        duplicate=self.ingest(name='another-name.txt',raw=b'a'*10)
        self.assertTrue(duplicate['duplicate']); self.assertEqual(duplicate['id'],first['id'])
        self.assertEqual(self.inventory(),before); self.assertEqual(self.size(),10)
        self.exceeds(b'b'*10)  # Same default filename never grants identity or overwrites bytes.
        self.assert_usable(first)
        # Raw accounting is directory-wide even if registry scope differs; ready dedup is playground-only.
        with reg.connect() as db:
            db.execute("UPDATE documents SET collection='other' WHERE id=?",(first['document_id'],))
        self.exceeds(b'a'*10)
        self.assertEqual(life.snapshot(),[])

    def test_replacement_overlap_exact_boundary_and_cleanup(self):
        self.full(10)
        old=self.ingest(raw=b'a'*6)
        self.exceeds(b'b'*5,old['document_id'],old['id'])
        self.assert_usable(old)
        new=self.ingest(raw=b'b'*4,did=old['document_id'],expected=old['id'])
        self.assertEqual(new['status'],'ready'); self.assertEqual(self.size(),10)
        self.assertEqual(set(self.stored()),{old['id'],new['id']})
        self.assertEqual([i['id'] for i in life.snapshot()],[new['id']]); self.assert_usable(new)
        before=self.stored()
        self.cleanup(); self.assertEqual(self.stored(),before)  # Dry run releases nothing.
        self.cleanup(True)
        self.assertEqual(self.stored(),{new['id']:b'b'*4}); self.assert_usable(new)
        self.assertEqual(life.version(old['id'])['status'],'ready')  # History is not erased.
        self.exceeds(b'c'*7)
        self.assertEqual(self.ingest(raw=b'c'*6)['status'],'ready')
        self.assertEqual(self.size(),10)

    def test_failed_replacement_retains_bytes_and_old_active_version(self):
        self.full(10)
        old=self.ingest(raw=b'a'*6)
        with patch.object(life.indexer,'index_documents',side_effect=RuntimeError('TEST index failure')):
            failed=self.ingest(raw=b'b'*4,did=old['document_id'],expected=old['id'])
        self.assertEqual(failed['status'],'failed'); self.assertEqual(self.size(),10)
        self.assertEqual([i['id'] for i in life.snapshot()],[old['id']]); self.assert_usable(old)
        self.exceeds(b'c')
        self.cleanup(True)
        self.assertEqual(self.stored(),{old['id']:b'a'*6}); self.assert_usable(old)

    def test_rejected_raw_is_retained_but_prevalidation_rejection_allocates_nothing(self):
        self.full(10)
        old=self.ingest(raw=b'a'*6)
        rejected=self.ingest(raw=b'\xff'*4)
        self.assertEqual(rejected['status'],'rejected'); self.assertEqual(self.size(),10)
        self.assertEqual([i['id'] for i in life.snapshot()],[old['id']])
        self.exceeds(b'b')
        self.exceeds(b'\xff'*4)  # Rejected attempts do not qualify for ready-content dedup.
        before=self.inventory(),self.stored()
        for name,raw in (('bad.exe',b'x'),('empty.txt',b'')):
            with self.assertRaises(life.LifecycleError):self.ingest(name,raw)
            self.assertEqual((self.inventory(),self.stored()),before)
        self.cleanup(True)
        self.assertEqual(self.stored(),{old['id']:b'a'*6}); self.assert_usable(old)

    def test_partial_raw_counts_until_explicit_cleanup(self):
        self.full(10)
        old=self.ingest(raw=b'a'*6)
        parsed={'status':'needs_review','blocks':[{'text':'Partial policy','page':1,'section':'page 1'}],
                'warnings':['unread page'],'parser_version':'TEST ONLY'}
        with patch.object(life,'parse',return_value=parsed):
            partial=self.ingest(raw=b'b'*4)
        self.assertEqual(partial['status'],'needs_review'); self.assertEqual(self.size(),10)
        self.assertEqual([i['id'] for i in life.snapshot()],[old['id']])
        self.exceeds(b'c')
        self.cleanup(True)
        self.assertEqual(self.stored(),{old['id']:b'a'*6}); self.assert_usable(old)

    def test_concurrent_distinct_uploads_cannot_both_fit(self):
        self.full(10)
        start=Barrier(2)
        def upload(raw):
            start.wait(timeout=10)
            try:return self.ingest(raw=raw)
            except life.LifecycleError as exc:return {'status':'rejected','code':exc.code}
        with ThreadPoolExecutor(2) as pool:
            results=list(pool.map(upload,(b'a'*6,b'b'*6)))
        self.assertEqual(sorted(r['status'] for r in results),['ready','rejected'])
        self.assertEqual(next(r for r in results if r['status']=='rejected')['code'],413)
        self.assertEqual(self.size(),6); self.assertEqual(len(life.snapshot()),1)
        self.assertEqual(len(self.stored()),1)
        self.assert_usable(next(r for r in results if r['status']=='ready'))
        self.assertEqual(self.ingest(raw=b'c'*4)['status'],'ready'); self.assertEqual(self.size(),10)

    def test_interruption_orphan_restart_and_cleanup_preserve_active_files(self):
        self.full(10)
        old=self.ingest(raw=b'a'*6)
        # Simulate abrupt termination after writing full raw bytes, before extraction completes.
        with patch.object(life,'parse',side_effect=KeyboardInterrupt('TEST interruption')):
            with self.assertRaises(KeyboardInterrupt):self.ingest(raw=b'b'*3)
        interrupted=next(v for v in life.list_documents() if v['id']!=old['id'])
        self.assertEqual(interrupted['status'],'parsing')
        orphan=reg.ROOT/'raw'/'interrupted-before-registry'; orphan.write_bytes(b'x')
        outside=reg.ROOT/'not-an-upload'; outside.write_bytes(b'preserve me')
        self.assertEqual(self.size(),10)
        reg.initialize(); reg.recover()  # Reopen durable DB; do not clear filesystem or reset counters.
        self.assertEqual(life.version(interrupted['id'])['status'],'failed')
        self.assertEqual(self.size(),10); self.exceeds(b'c'); self.assert_usable(old)
        self.cleanup(True)
        self.assertEqual(self.stored(),{old['id']:b'a'*6})
        self.assertEqual(outside.read_bytes(),b'preserve me'); self.assert_usable(old)
        self.assertEqual(self.ingest(raw=b'c'*4)['status'],'ready'); self.assertEqual(self.size(),10)

    def test_logical_delete_does_not_release_capacity_until_cleanup(self):
        self.full(10)
        old=self.ingest(raw=b'a'*6); deleted=self.ingest(raw=b'b'*4)
        life.delete(deleted['document_id'],deleted['id'])
        self.assertEqual(self.size(),10); self.exceeds(b'c'); self.assert_usable(old)
        self.assertEqual([i['id'] for i in life.snapshot()],[old['id']])
        self.cleanup(True)
        self.assertEqual(self.stored(),{old['id']:b'a'*6})
        self.assertEqual(life.version(deleted['id'])['status'],'deleted')
        self.assertEqual(self.ingest(raw=b'c'*4)['status'],'ready'); self.assertEqual(self.size(),10)

    def test_api_batch_and_replacement_report_capacity_rejection(self):
        self.full(10)
        with TestClient(app) as api:
            r=api.post('/documents',files=[('files',('policy.txt',b'a'*6)),('files',('second.txt',b'b'*5))])
            self.assertEqual(r.status_code,201)  # Per-file results, not whole-batch rollback.
            good,bad=r.json()['outcomes']
            self.assertEqual(good['status'],'ready'); self.assertEqual(bad['status'],'rejected')
            self.assertEqual(bad['http_status'],413); self.assertEqual(self.size(),6)
            r=api.post('/documents/'+good['document_id']+'/replace',params={'expected_version':good['id']},
                       files={'file':('replacement.txt',b'c'*5)})
            self.assertEqual(r.status_code,413)
            self.assertEqual([i['id'] for i in life.snapshot()],[good['id']]); self.assert_usable(good)
            self.assertEqual(self.size(),6)
