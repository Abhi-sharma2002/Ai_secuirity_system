"""Shared integrity checks for A/B prompt preparation; no content filtering."""
import hashlib
import json
from dataclasses import asdict

from app.legacy.defenses.base import PromptPreparationError
from app.evaluation.evidence_builder import EvidencePackage


def validate_evidence(package: EvidencePackage) -> None:
    if not isinstance(package, EvidencePackage):
        raise PromptPreparationError('Expected a Phase 3 EvidencePackage')
    if package.schema_version != 1 or package.evidence_mode != 'fixed_context':
        raise PromptPreparationError('Unsupported evidence schema or mode')
    try:
        payload = asdict(package)
        fingerprint = payload.pop('fingerprint')
        actual = hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True,
                                          separators=(',', ':')).encode('utf-8')).hexdigest()
        if fingerprint != actual:
            raise PromptPreparationError('Evidence fingerprint mismatch')
        if (not package.document_ids or len(package.document_ids) != len(package.documents)
                or len(package.documents) != len(package.boundaries)
                or len(set(package.document_ids)) != len(package.document_ids)):
            raise PromptPreparationError('Evidence source inventory mismatch')
        raw = package.evidence_text.encode('utf-8')
        if package.character_count != len(package.evidence_text) or package.byte_count != len(raw):
            raise PromptPreparationError('Evidence counts mismatch')
        for document_id, document, boundary in zip(package.document_ids, package.documents, package.boundaries):
            if (document_id != document.document_id or document_id != boundary.document_id
                    or not 0 <= boundary.start_char < boundary.end_char <= len(package.evidence_text)
                    or not 0 <= boundary.start_byte < boundary.end_byte <= len(raw)
                    or package.evidence_text[boundary.start_char:boundary.end_char] != document.content
                    or raw[boundary.start_byte:boundary.end_byte] != document.content.encode('utf-8')
                    or len(package.evidence_text[:boundary.start_char].encode('utf-8')) != boundary.start_byte
                    or len(package.evidence_text[:boundary.end_char].encode('utf-8')) != boundary.end_byte
                    or hashlib.sha256(document.content.encode('utf-8')).hexdigest() != document.sha256):
                raise PromptPreparationError('Evidence source boundaries or checksums mismatch')
    except PromptPreparationError:
        raise
    except (TypeError, ValueError, AttributeError, KeyError):
        raise PromptPreparationError('Invalid evidence package') from None

