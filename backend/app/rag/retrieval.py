"""Active-version retrieval and bounded evidence assembly, without provider calls."""
from app.core.config import settings
from app.ingestion.lifecycle import snapshot
from app.rag import indexer


def search(question, items=None):
    from app.rag.retriever import DocumentRetriever
    items = snapshot() if items is None else items
    hits = []
    for item in items:
        found = DocumentRetriever(item['index_name']).search(question, {item['document_id']}, settings.top_k)
        # All provenance comes from the immutable registry/version, never uploaded claims.
        collection = indexer.get_client().get_collection(item['index_name'], embedding_function=None)
        metadata = collection.get(ids=[h.chunk_id for h in found], include=['metadatas'])
        lookup = dict(zip(metadata['ids'], metadata['metadatas']))
        for hit in found:
            extra = lookup[hit.chunk_id]
            hits.append({'id': hit.chunk_id, 'document_id': item['document_id'], 'version_id': item['id'],
                'sha256': item['sha256'], 'filename': item['filename'], 'text': hit.content,
                'page': extra.get('page', 0), 'section': extra.get('section', ''),
                'partial_text': item.get('partial_accepted', False), 'distance': hit.distance})
    hits.sort(key=lambda h: (h['distance'], h['id']))
    selected, omitted, size = [], [], 0
    for hit in hits:
        if len(selected) >= settings.top_k or size + len(hit['text'].encode()) > 12_000:
            omitted.append(hit['id'])
        else:
            selected.append(hit)
            size += len(hit['text'].encode())
    return {'hits': selected, 'omitted_ids': omitted, 'snapshot': [{'document_id': i['document_id'], 'version_id': i['id'], 'sha256': i['sha256'], 'index': i['index_name']} for i in items], 'score_meaning': 'cosine distance; smaller is closer, not confidence'}
