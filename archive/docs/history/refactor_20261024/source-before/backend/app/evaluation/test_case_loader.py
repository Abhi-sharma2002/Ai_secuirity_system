"""Validate evaluation inputs without screening, scoring, retrieval or LLM calls.

Records are returned unchanged, including Unicode evidence and human-review metadata.
The document_ids field describes evaluation evidence; it is NOT an authorization grant.
"""
import hashlib
import json
import os
import re
import stat
from pathlib import Path
from collections.abc import Mapping

from app.core.config import ROOT, settings
from app.ingestion.loader import DOCUMENT_PATTERN

DEFAULT_TEST_CASES = ROOT / 'data/test_cases/test_cases_verified.json'
DEFAULT_MANIFEST = ROOT / 'data/manifests/documents_manifest.json'
TEST_FAMILIES = frozenset({'legitimate_quality', 'benign_quotation', 'attack'})
# Only the mode actually specified by this schema is accepted. Future RAG cases
# need an explicit schema extension, not reinterpretation of fixed-context cases.
EVIDENCE_MODES = frozenset({'fixed_context'})
SCREENING_LABELS = frozenset({'benign', 'suspicious'})
TEXT_FIELDS = (
    'test_id', 'source_test_id', 'domain', 'test_family', 'risk_category',
    'question', 'evidence_mode', 'expected_answer_supported_by_document',
    'exact_supporting_quote', 'supporting_section', 'supporting_document_sha256',
    'expected_screening_label', 'attack_success_definition', 'task_success_definition',
    'citation_success_definition', 'attack_exposure_check', 'scoring_policy',
    'review_status', 'notes',
)
FIXTURE_FIELDS = ('document_id', 'source_path', 'section', 'section_text_exact',
                  'attack_goal_category', 'attack_indicator_from_source')
DOCUMENT_ID = re.compile(r'D[0-9]{3}')
SHA256 = re.compile(r'[0-9a-f]{64}')
SECTION_HEADING = re.compile(r'^[0-9]+\. [^\r\n]+', re.MULTILINE)


class TestCaseValidationError(ValueError):
    """Invalid dataset structure or unverifiable source evidence."""


def _read_source(path: Path, description: str, limit: int) -> tuple[str, str]:
    """Read bounded UTF-8 bytes; refuse symlinks in every path component.

    Linux dir_fd opens pin each parent directory, avoiding check-then-open races.
    No path or document text is interpolated into a shell command or error.
    """
    if '..' in path.parts:
        raise TestCaseValidationError(f'{description}: parent traversal is forbidden')
    absolute = Path(os.path.abspath(path))
    parent_fd = None
    try:
        parent_fd = os.open(absolute.anchor, os.O_RDONLY | os.O_DIRECTORY)
        for part in absolute.parts[1:-1]:
            next_fd = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                              dir_fd=parent_fd)
            os.close(parent_fd)
            parent_fd = next_fd
        fd = os.open(absolute.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK,
                     dir_fd=parent_fd)
        with os.fdopen(fd, 'rb') as source:
            info = os.fstat(source.fileno())
            if not stat.S_ISREG(info.st_mode):
                raise TestCaseValidationError(f'{description}: expected a regular file')
            if info.st_size > limit:
                raise TestCaseValidationError(f'{description}: file exceeds size limit')
            raw = source.read(limit + 1)
            if len(raw) > limit:
                raise TestCaseValidationError(f'{description}: file exceeds size limit')
        return raw.decode('utf-8', errors='strict'), hashlib.sha256(raw).hexdigest()
    except (OSError, UnicodeError, ValueError) as exc:
        if isinstance(exc, TestCaseValidationError):
            raise
        raise TestCaseValidationError(
            f'{description}: cannot read regular UTF-8 file (missing, unreadable or unsafe path)'
        ) from exc
    finally:
        if parent_fd is not None:
            os.close(parent_fd)


def _unique_object(pairs: list[tuple]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise TestCaseValidationError('JSON object contains duplicate keys')
        result[key] = value
    return result


def _read_json_array(path: Path, description: str) -> list:
    text, _ = _read_source(path, description, 8 * 1024 * 1024)
    try:
        records = json.loads(text, object_pairs_hook=_unique_object,
                             parse_constant=_reject_json_constant)
    except (ValueError, RecursionError) as exc:
        raise TestCaseValidationError(f'{description}: invalid JSON') from exc
    if not isinstance(records, list) or not records:
        raise TestCaseValidationError(f'{description}: expected a nonempty JSON array')
    return records


def _reject_json_constant(value: str) -> None:
    raise TestCaseValidationError('Nonstandard JSON numeric constant')


def _require_text(record: dict, fields: tuple[str, ...], allow_empty: tuple[str, ...] = ()) -> None:
    for field in fields:
        if not isinstance(record.get(field), str):
            raise TestCaseValidationError(f'{field}: required string')
        if field not in allow_empty and not record[field].strip():
            raise TestCaseValidationError(f'{field}: cannot be empty')


def _load_manifest(path: Path) -> dict[str, dict]:
    manifest = {}
    for position, item in enumerate(_read_json_array(path, 'document manifest'), 1):
        try:
            if not isinstance(item, dict):
                raise TestCaseValidationError('expected an object')
            _require_text(item, ('document_id', 'source_file', 'sha256'))
            document_id = item['document_id']
            if not DOCUMENT_ID.fullmatch(document_id):
                raise TestCaseValidationError('invalid document_id')
            if document_id in manifest:
                raise TestCaseValidationError('duplicate document_id')
            source = item['source_file']
            # Manifest paths are data-root relative, with exactly one filename.
            parts = source.split('/')
            match = DOCUMENT_PATTERN.fullmatch(parts[-1])
            if (len(parts) != 2 or parts[0] != 'documents' or
                    not match or match.group(1) != document_id):
                raise TestCaseValidationError('unsafe or inconsistent source_file')
            if not SHA256.fullmatch(item['sha256']):
                raise TestCaseValidationError('invalid sha256')
            manifest[document_id] = item
        except TestCaseValidationError as exc:
            raise TestCaseValidationError(f'manifest record {position}: {exc}') from exc
    return manifest


def read_verified_document(entry: Mapping[str, str], document_directory: str | Path) -> dict:
    """Read a validated manifest entry and verify its original UTF-8 bytes.

    The entry must come from _load_manifest; no path from a test case is opened.
    Shared by dataset validation and fixed-context evidence construction.
    """
    document_id = entry['document_id']
    content, checksum = _read_source(
        Path(document_directory) / entry['source_file'].split('/')[1],
        f'source {document_id}', settings.max_file_size)
    if checksum != entry['sha256']:
        raise TestCaseValidationError(f'manifest hash mismatch for {document_id}')
    return {'content': content, 'sha256': checksum}


def _section_content(content: str, heading: str) -> str:
    headings = list(SECTION_HEADING.finditer(content))
    matches = [i for i, match in enumerate(headings) if match.group() == heading]
    if len(matches) != 1:
        raise TestCaseValidationError('source section is missing or ambiguous')
    index = matches[0]
    start = headings[index].end()
    end = headings[index + 1].start() if index + 1 < len(headings) else len(content)
    # Exclude the container's separating newlines; never strip/normalize payload text.
    return content[start:end].strip('\r\n')


def _validate_case(case: dict, manifest: dict, documents: dict[str, dict],
                   document_directory: Path) -> None:
    _require_text(case, TEXT_FIELDS, allow_empty=('notes', 'supporting_document_sha256'))
    if not re.fullmatch(r'E[0-9]{3}', case['test_id']):
        raise TestCaseValidationError('test_id: expected E followed by three ASCII digits')
    if not re.fullmatch(r'T[0-9]{3}', case['source_test_id']):
        raise TestCaseValidationError('source_test_id: expected T followed by three ASCII digits')
    for field, choices in (('test_family', TEST_FAMILIES), ('evidence_mode', EVIDENCE_MODES),
                           ('expected_screening_label', SCREENING_LABELS)):
        if case[field] not in choices:
            raise TestCaseValidationError(f'{field}: unsupported value')
    for field in ('tool_execution_required', 'human_review_required'):
        if type(case.get(field)) is not bool:
            raise TestCaseValidationError(f'{field}: required boolean')
    ids = case.get('document_ids')
    if not isinstance(ids, list) or not ids:
        raise TestCaseValidationError('document_ids: expected a nonempty list')
    seen = set()
    for document_id in ids:
        if not isinstance(document_id, str) or not DOCUMENT_ID.fullmatch(document_id):
            raise TestCaseValidationError('document_ids: invalid document ID')
        if document_id in seen:
            raise TestCaseValidationError('document_ids: duplicate document ID')
        seen.add(document_id)
        if document_id not in manifest:
            raise TestCaseValidationError(f'unknown document ID: {document_id}')
        if document_id not in documents:
            documents[document_id] = read_verified_document(manifest[document_id], document_directory)
    supporting_id = case['expected_answer_supported_by_document']
    if supporting_id not in seen:
        raise TestCaseValidationError('supporting document must be in document_ids')
    supporting = documents[supporting_id]
    checksum = case['supporting_document_sha256']
    if checksum and (not SHA256.fullmatch(checksum) or checksum != supporting['sha256']):
        raise TestCaseValidationError('supporting_document_sha256: hash mismatch')
    section = _section_content(supporting['content'], case['supporting_section'])
    if case['exact_supporting_quote'] not in section:
        raise TestCaseValidationError('exact_supporting_quote: not found in supporting section')
    if 'attack_fixture' not in case:
        raise TestCaseValidationError('attack_fixture: required field (object or null)')
    fixture = case['attack_fixture']
    if case['test_family'] != 'attack':
        if fixture is not None:
            raise TestCaseValidationError('non-attack family requires a null attack_fixture')
        if case['expected_screening_label'] != 'benign':
            raise TestCaseValidationError('non-attack family requires the declared benign label')
        for field in ('attack_success_definition', 'attack_exposure_check'):
            if case[field] != 'not_applicable':
                raise TestCaseValidationError(f'{field}: must be not_applicable for a non-attack case')
        return
    if case['expected_screening_label'] != 'suspicious':
        raise TestCaseValidationError('attack family requires the declared suspicious label')
    if not isinstance(fixture, dict):
        raise TestCaseValidationError('attack_fixture: attack cases require an object')
    _require_text(fixture, FIXTURE_FIELDS)
    fixture_id = fixture['document_id']
    if fixture_id not in seen:
        raise TestCaseValidationError('attack_fixture.document_id: must be in document_ids')
    if fixture['source_path'] != manifest[fixture_id]['source_file']:
        raise TestCaseValidationError('attack_fixture.source_path: must equal the manifest source_file')
    original_section = _section_content(documents[fixture_id]['content'], fixture['section'])
    if fixture['section_text_exact'] != original_section:
        raise TestCaseValidationError('attack_fixture.section_text_exact: source section mismatch')
    if fixture['attack_indicator_from_source'] not in original_section:
        raise TestCaseValidationError('attack_fixture.attack_indicator_from_source: absent from source section')
    for field in ('attack_success_definition', 'attack_exposure_check'):
        if case[field] == 'not_applicable':
            raise TestCaseValidationError(f'{field}: required for attack cases')


def load_test_cases(
    path: str | Path = DEFAULT_TEST_CASES,
    manifest_path: str | Path = DEFAULT_MANIFEST,
    document_directory: str | Path = settings.document_directory,
) -> list[dict]:
    """Return original records only after every case and referenced source verifies.

    An empty supporting hash is allowed when not provided; manifest hashes remain
    mandatory. No ground-truth values are inferred, filled in or rewritten.
    """
    cases = _read_json_array(Path(path), 'test-case dataset')
    manifest = _load_manifest(Path(manifest_path))
    documents: dict[str, dict] = {}
    seen_ids = set()
    for position, case in enumerate(cases, 1):
        # Only syntactically safe IDs may appear in diagnostics, never arbitrary payloads.
        test_id = case.get('test_id') if isinstance(case, dict) else None
        label = test_id if isinstance(test_id, str) and re.fullmatch(r'E[0-9]{3}', test_id) else f'record {position}'
        try:
            if not isinstance(case, dict):
                raise TestCaseValidationError('expected an object')
            _validate_case(case, manifest, documents, Path(document_directory))
            if case['test_id'] in seen_ids:
                raise TestCaseValidationError('duplicate test_id')
            seen_ids.add(case['test_id'])
        except TestCaseValidationError as exc:
            raise TestCaseValidationError(f'{label}: {exc}') from exc
    return cases
