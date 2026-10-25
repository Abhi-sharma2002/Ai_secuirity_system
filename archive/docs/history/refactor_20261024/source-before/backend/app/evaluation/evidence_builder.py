"""Deterministic full-document evidence, shared unchanged across future defenses.

No retrieval, screening, prompts, scoring labels or LLM calls belong here.
"""
import hashlib
import json
import re
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from types import MappingProxyType
from typing import Mapping

from app.core.config import settings
from app.evaluation.test_case_loader import (
    DEFAULT_MANIFEST, DOCUMENT_ID, TestCaseValidationError,
    _load_manifest, read_verified_document,
)

# Only source provenance is exposed; manifest attack labels remain evaluation-only.
PROVENANCE_FIELDS = ('domain', 'classification', 'owner', 'version', 'effective_date')


class EvidenceBuildError(ValueError):
    """Evidence cannot be built without violating integrity or size constraints."""


@dataclass(frozen=True)
class VerifiedSources:
    document_directory: Path
    manifest: Mapping[str, Mapping[str, str]]


@dataclass(frozen=True)
class EvidenceDocument:
    document_id: str
    title: str
    source_file: str
    sha256: str
    content: str
    metadata: tuple[tuple[str, str], ...]
    character_count: int
    byte_count: int


@dataclass(frozen=True)
class SourceBoundary:
    """Half-open offsets of original content within evidence_text/its UTF-8 bytes."""
    document_id: str
    start_char: int
    end_char: int
    start_byte: int
    end_byte: int


@dataclass(frozen=True)
class EvidencePackage:
    test_id: str
    question: str
    evidence_mode: str
    document_ids: tuple[str, ...]
    documents: tuple[EvidenceDocument, ...]
    evidence_text: str
    boundaries: tuple[SourceBoundary, ...]
    character_count: int
    byte_count: int
    source_character_count: int
    source_byte_count: int
    fingerprint: str = ''
    schema_version: int = 1


def load_verified_sources(
    manifest_path: str | Path = DEFAULT_MANIFEST,
    document_directory: str | Path = settings.document_directory,
) -> VerifiedSources:
    """Pin manifest expectations and verify sources; recheck files on every build.

    The read-only manifest prevents accidental in-process expectation changes.
    Call once per experiment and reuse it for every case and defense configuration.
    """
    try:
        manifest = _load_manifest(Path(manifest_path))
        for entry in manifest.values():
            for field in ('title', *PROVENANCE_FIELDS):
                if field in entry and (not isinstance(entry[field], str) or not entry[field].strip()):
                    raise EvidenceBuildError(f'{entry["document_id"]}: invalid source metadata field {field}')
            if 'title' not in entry:
                raise EvidenceBuildError(f'{entry["document_id"]}: missing source title')
            read_verified_document(entry, document_directory)
    except TestCaseValidationError as exc:
        raise EvidenceBuildError(str(exc)) from exc
    # Keep only immutable provenance and expected hashes, never attack annotations.
    fields = ('document_id', 'title', 'source_file', 'sha256', *PROVENANCE_FIELDS)
    pinned = {document_id: MappingProxyType({key: entry[key] for key in fields if key in entry})
              for document_id, entry in manifest.items()}
    return VerifiedSources(Path(document_directory).absolute(), MappingProxyType(pinned))


def _validate_inputs(test_case: dict, sources: VerifiedSources,
                     max_characters: int, max_bytes: int) -> tuple[str, ...]:
    if not isinstance(test_case, dict):
        raise EvidenceBuildError('Expected a validated test-case object')
    test_id = test_case.get('test_id')
    if not isinstance(test_id, str) or not re.fullmatch(r'E[0-9]{3}', test_id):
        raise EvidenceBuildError('Invalid test_id')
    question = test_case.get('question')
    if not isinstance(question, str) or not question.strip():
        raise EvidenceBuildError(f'{test_id}: question must be a nonempty string')
    try:
        question.encode('utf-8')
    except UnicodeError as exc:
        raise EvidenceBuildError(f'{test_id}: question is not valid UTF-8 text') from exc
    if test_case.get('evidence_mode') != 'fixed_context':
        raise EvidenceBuildError(f'{test_id}: expected fixed_context evidence_mode')
    ids = test_case.get('document_ids')
    if not isinstance(ids, list) or not ids:
        raise EvidenceBuildError(f'{test_id}: document_ids must be a nonempty list')
    if any(not isinstance(item, str) or not DOCUMENT_ID.fullmatch(item) for item in ids):
        raise EvidenceBuildError(f'{test_id}: invalid document ID')
    if len(set(ids)) != len(ids):
        raise EvidenceBuildError(f'{test_id}: duplicate document IDs')
    if not isinstance(sources, VerifiedSources):
        raise EvidenceBuildError(f'{test_id}: expected verified document sources')
    for name, limit in (('max_characters', max_characters), ('max_bytes', max_bytes)):
        if type(limit) is not int or limit <= 0:
            raise EvidenceBuildError(f'{test_id}: {name} must be a positive integer')
    return tuple(ids)


def build_evidence(
    test_case: dict,
    sources: VerifiedSources,
    *,
    max_characters: int = settings.evidence_max_characters,
    max_bytes: int = settings.evidence_max_bytes,
) -> EvidencePackage:
    """Build from a validated case and pinned sources, preserving every source byte.

    Limits cover the complete framed evidence, including separators, excluding the
    separate question. Missing/changed files fail even after sources were loaded.
    """
    ids = _validate_inputs(test_case, sources, max_characters, max_bytes)
    test_id = test_case['test_id']
    documents, boundaries, parts = [], [], []
    char_offset = byte_offset = 0
    source_chars = source_bytes = 0
    for position, document_id in enumerate(ids, 1):
        entry = sources.manifest.get(document_id)
        if entry is None:
            raise EvidenceBuildError(f'{test_id}: missing referenced source {document_id}')
        try:
            verified = read_verified_document(entry, sources.document_directory)
        except TestCaseValidationError as exc:
            raise EvidenceBuildError(f'{test_id}: {exc}') from exc
        # The dataset loader verifies quotes/fixtures. Recheck its supporting hash
        # here to catch accidentally combining a case with another source version.
        if (test_case.get('expected_answer_supported_by_document') == document_id and
                test_case.get('supporting_document_sha256') and
                test_case['supporting_document_sha256'] != verified['sha256']):
            raise EvidenceBuildError(f'{test_id}: supporting hash mismatch for {document_id}')
        content = verified['content']
        chars, byte_count = len(content), len(content.encode('utf-8'))
        header = f'=== BEGIN SOURCE {position:03d} {document_id} SHA256 {verified["sha256"]} ===\n'
        footer = f'\n=== END SOURCE {position:03d} {document_id} ===\n'
        framed_chars = len(header) + chars + len(footer)
        framed_bytes = len(header.encode('utf-8')) + byte_count + len(footer.encode('utf-8'))
        if char_offset + framed_chars > max_characters or byte_offset + framed_bytes > max_bytes:
            raise EvidenceBuildError(f'{test_id}: evidence exceeds configured size limit; no content truncated')
        start_char = char_offset + len(header)
        start_byte = byte_offset + len(header.encode('utf-8'))
        boundaries.append(SourceBoundary(document_id, start_char, start_char + chars,
                                          start_byte, start_byte + byte_count))
        documents.append(EvidenceDocument(
            document_id, entry['title'], entry['source_file'], verified['sha256'], content,
            tuple((key, entry[key]) for key in PROVENANCE_FIELDS if key in entry), chars, byte_count))
        parts.extend((header, content, footer))
        char_offset += framed_chars
        byte_offset += framed_bytes
        source_chars += chars
        source_bytes += byte_count
    package = EvidencePackage(
        test_id, test_case['question'], 'fixed_context', ids, tuple(documents), ''.join(parts),
        tuple(boundaries), char_offset, byte_offset, source_chars, source_bytes)
    # Canonical JSON includes question, ordered sources, provenance, framing, counts
    # and schema version. No runtime paths, timestamps or defense settings enter it.
    payload = asdict(package)
    del payload['fingerprint']
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
    fingerprint = hashlib.sha256(canonical.encode('utf-8')).hexdigest()
    return replace(package, fingerprint=fingerprint)
