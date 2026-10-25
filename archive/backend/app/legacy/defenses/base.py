"""Shared preparation/result records; no screening, grading, or provider policy."""
import hashlib
import json
from dataclasses import asdict, dataclass, field

from legacy_llm.client import LLMResult
from legacy_llm.models import LLMRequest
from legacy_llm.usage import RequestRecord


class PromptPreparationError(ValueError):
    """Evidence cannot be prepared without violating the input contract."""


@dataclass(frozen=True)
class DeliveredSource:
    """Half-open source offsets inside a specific application message."""
    document_id: str
    message_index: int
    start_char: int
    end_char: int
    start_byte: int
    end_byte: int


@dataclass(frozen=True)
class PreparedPrompt:
    request: LLMRequest = field(repr=False)
    prompt_version: str
    model_input_fingerprint: str
    document_ids: tuple[str, ...]
    delivered_sources: tuple[DeliveredSource, ...]

    def safe_metadata(self) -> dict:
        return {
            'test_id': self.request.test_id,
            'configuration_id': self.request.configuration_id,
            'evidence_fingerprint': self.request.evidence_fingerprint,
            'prompt_version': self.prompt_version,
            'message_roles': [message.role for message in self.request.messages],
            'untrusted_message_indices': [index for index, message in enumerate(self.request.messages)
                                          if message.untrusted],
            'model_input_fingerprint': self.model_input_fingerprint,
            'document_ids': list(self.document_ids),
            'delivered_sources': [asdict(source) for source in self.delivered_sources],
        }


@dataclass(frozen=True)
class DefenseResult:
    prepared: PreparedPrompt = field(repr=False)
    completion: LLMResult = field(repr=False)

    def safe_metadata(self) -> dict:
        return {**self.prepared.safe_metadata(), 'llm': self.completion.record.to_dict()}


class DefenseExecutionError(RuntimeError):
    """Preserve prompt provenance and usage on a failed attempted model call."""
    def __init__(self, prepared: PreparedPrompt, record: RequestRecord):
        self.prepared = prepared
        self.record = record
        super().__init__('Defense model call failed; inspect the structured usage record')


def fingerprint_request(request: LLMRequest, prompt_version: str) -> str:
    """Application-message hash, not a hash of an unknown provider wire format."""
    payload = {
        'schema_version': 1, 'prompt_version': prompt_version,
        'configuration_id': request.configuration_id,
        'messages': [asdict(message) for message in request.messages],
        'temperature': request.temperature, 'max_output_tokens': request.max_output_tokens,
    }
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True,
                                     separators=(',', ':')).encode('utf-8')).hexdigest()
