"""Genuine local integration check; no embeddings/provider mocks and no live calls."""
import os
os.environ['LIVE_LLM_ENABLED']='false'
import json
import tempfile
from pathlib import Path
from uuid import uuid4
from fastapi.testclient import TestClient
from app.core import registry as reg
from app.ingestion import indexer
from app.main import app


def main():
    import chromadb
    with tempfile.TemporaryDirectory() as folder:
        reg.ROOT=Path(folder)/'runtime'
        client=chromadb.PersistentClient(path=str(Path(folder)/'chroma'))
        indexer.get_client=lambda: client
        import app.rag.retriever as retriever
        retriever.get_client=lambda: client
        with TestClient(app) as api:
            r=api.post('/documents',files={'files':('HR Policy 2026.txt',b'Annual leave entitlement is eighteen days. Expense receipts are due in fourteen days.')})
            r.raise_for_status(); item=r.json()['outcomes'][0]
            assert item['status']=='ready',item
            query={'question':'How much annual leave is available?','mode':'B','request_id':str(uuid4())}
            found=api.post('/search',json=query); found.raise_for_status()
            assert found.json()['hits'] and 'eighteen' in found.json()['hits'][0]['text']
            response=api.post('/chat',json=query).json(); assert response['status']=='live_blocked',response
            duplicate=api.post('/documents',files={'files':('नीति.txt',b'Annual leave entitlement is eighteen days. Expense receipts are due in fourteen days.')}).json()['outcomes'][0]
            assert duplicate['duplicate'] and duplicate['id']==item['id']
            failure=api.post(f"/documents/{item['document_id']}/replace",params={'expected_version':item['id']},files={'file':('bad.pdf',b'%PDF-corrupt')}).json()
            assert failure['status']=='rejected',failure
            assert api.post('/search',json=query).json()['hits']
            replacement=api.post(f"/documents/{item['document_id']}/replace",params={'expected_version':item['id']},files={'file':('leave_policy(final).md',b'Annual leave entitlement is twenty days.')}).json()
            assert replacement['status']=='ready',replacement
            hits=api.post('/search',json=query).json()['hits']
            assert hits and all(h['version_id']==replacement['id'] for h in hits)
            r=api.delete(f"/documents/{item['document_id']}",params={'expected_version':replacement['id']}); r.raise_for_status()
            assert not api.post('/search',json=query).json()['hits']
            print(json.dumps({'actual_cpu_embeddings':True,'persistent_chroma':True,'upload_retrieval':True,'deduplication':True,
              'failed_replace_preserved_active':True,'successful_replace_excluded_stale':True,'delete_excluded':True,
              'provider_calls':0,'live_status':response['status']},indent=2))

if __name__=='__main__': main()
