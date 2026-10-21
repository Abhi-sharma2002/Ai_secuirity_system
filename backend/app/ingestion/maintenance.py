"""Explicit cleanup/rebuild; stop backend before running. No historical erasure claim."""
import argparse
import json
from pathlib import Path
from app.core import registry as reg
from app.ingestion import indexer
from app.ingestion.lifecycle import _chunks
from app.ingestion.parsers import PARSER_VERSION


def main():
    import fcntl
    p=argparse.ArgumentParser();p.add_argument('command',choices=['cleanup','rebuild']);p.add_argument('--apply',action='store_true');args=p.parse_args()
    reg.initialize()
    with (reg.ROOT/'backend.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        with reg.connect() as db:
            rows=db.execute('SELECT * FROM versions').fetchall()
            active={r[0] for r in db.execute('SELECT active_version FROM documents WHERE active_version IS NOT NULL AND deleted=0')}
        versions=[reg.decoded(r) for r in rows]
        if args.command=='rebuild':
            for item in versions:
                if item['id'] not in active:continue
                if item.get('parser_version')!=PARSER_VERSION:raise ValueError('Parser fingerprint changed; explicitly replace from original source after reviewing extraction')
                print(json.dumps({'rebuild_version':item['id'],'apply':args.apply}))
                if args.apply:
                    # Staged index verification then CAS swap. Old index remains until later cleanup.
                    result=indexer.index_documents(_chunks(item))
                    with reg.connect() as db:
                        db.execute('UPDATE versions SET index_name=? WHERE id=? AND id IN (SELECT active_version FROM documents WHERE deleted=0)',(result['collection'],item['id']))
        else:
            retained={v['index_name'] for v in versions if v['id'] in active}
            snapshot=Path(__file__).resolve().parents[2]/'benchmark/snapshot.json'
            if snapshot.exists():retained.update(v['index_name'] for v in json.loads(snapshot.read_text())['items'].values())
            # Saved experiments preserve immutable version records and vectors as explicit historical retention.
            for exp in (reg.ROOT/'experiments').glob('*/case-*.json'):
                row=json.loads(exp.read_text())
                retained.update(s['index'] for s in row['response'].get('snapshot',[]))
            for collection in indexer.get_client().list_collections():
                if collection.name not in retained:
                    print(json.dumps({'delete_orphan_index':collection.name,'apply':args.apply}))
                    if args.apply:indexer.get_client().delete_collection(collection.name)
            for item in versions:
                if item['id'] in active:continue
                raw=reg.ROOT/'raw'/item['id']
                if raw.exists():
                    print(json.dumps({'delete_inactive_raw':item['id'],'apply':args.apply}))
                    if args.apply:raw.unlink()
            for temp in (reg.ROOT/'raw').glob('*'):
                if temp.name not in {v['id'] for v in versions}:
                    print(json.dumps({'delete_interrupted_raw':temp.name,'apply':args.apply}))
                    if args.apply:temp.unlink()

if __name__=='__main__':main()
