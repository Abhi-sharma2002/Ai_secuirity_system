"""SQLite persistence; one backend process owns all writes."""
import json
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from threading import RLock
from app.core.config import settings

ROOT = settings.app_data_directory
LOCK = RLock()


@contextmanager
def connect():
    ROOT.mkdir(parents=True, exist_ok=True, mode=0o700)
    db = sqlite3.connect(ROOT / 'registry.sqlite3', timeout=30)
    db.row_factory = sqlite3.Row
    db.execute('PRAGMA foreign_keys=ON')
    try:
        yield db
        db.commit()
    except BaseException:
        db.rollback()
        raise
    finally:
        db.close()


def initialize():
    with connect() as db:
        db.executescript('''
        CREATE TABLE IF NOT EXISTS schema_migrations(version INTEGER PRIMARY KEY);
        INSERT OR IGNORE INTO schema_migrations VALUES(1);
        CREATE TABLE IF NOT EXISTS documents(id TEXT PRIMARY KEY, collection TEXT NOT NULL,
          active_version TEXT, deleted INTEGER NOT NULL DEFAULT 0);
        CREATE TABLE IF NOT EXISTS versions(id TEXT PRIMARY KEY, document_id TEXT NOT NULL REFERENCES documents(id),
          filename TEXT NOT NULL, sha256 TEXT NOT NULL, status TEXT NOT NULL, created TEXT NOT NULL,
          index_name TEXT, data TEXT NOT NULL, expected_version TEXT);
        CREATE TABLE IF NOT EXISTS requests(id TEXT PRIMARY KEY, fingerprint TEXT NOT NULL, result TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS allowance(id TEXT PRIMARY KEY, calls INTEGER NOT NULL, tokens INTEGER NOT NULL,
          stopped INTEGER NOT NULL DEFAULT 0);
        CREATE TABLE IF NOT EXISTS calls(id TEXT PRIMARY KEY, allowance_id TEXT, stage TEXT, status TEXT,
          data TEXT NOT NULL);
        ''')


def recover():
    # An unactivated index can remain on disk, but never becomes retrieval eligible.
    with connect() as db:
        db.execute("UPDATE versions SET status='failed' WHERE status IN ('received','validating','parsing','indexing')")
        db.execute("UPDATE calls SET status='unknown' WHERE status='started'")


def decoded(row):
    if row is None:
        raise KeyError('Document or version not found')
    value = dict(row)
    payload = json.loads(value.pop('data', '{}'))
    value = {**payload, **value}
    return value
