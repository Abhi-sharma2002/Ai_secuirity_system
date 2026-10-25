"""One-case baseline execution and explicit, private result recording. No scoring."""
import json
import os
import re
import shutil
from dataclasses import asdict, dataclass, field
from pathlib import Path
from uuid import uuid4

from app.legacy.defenses.base import DefenseExecutionError, PreparedPrompt, PromptPreparationError
from app.legacy.defenses.baseline import BaselineDefense
from app.evaluation.evidence_builder import EvidencePackage, VerifiedSources, build_evidence, load_verified_sources
from app.evaluation.legacy_rubrics import for_case as legacy_rubric_for_case
from legacy_llm.client import LLMClient
from legacy_llm.fake import FakeAdapter
from legacy_llm.usage import RequestRecord

# These are mentions/candidates, not verified citations or a quality score.
DOCUMENT_MENTION = re.compile(r'(?<![A-Za-z0-9_])D[0-9]{3}(?![A-Za-z0-9_])')


@dataclass(frozen=True)
class CitationCandidate:
    document_id: str
    start_char: int
    end_char: int
    in_supplied_evidence: bool
    validation_status: str = 'not_validated'


@dataclass(frozen=True)
class AnswerContent:
    question: str = field(repr=False)
    answer: str | None = field(repr=False)
    citation_candidates: tuple[CitationCandidate, ...] = field(repr=False)


@dataclass(frozen=True)
class BaselineExecution:
    """Reusable execution schema: untrusted text is separate from operational data."""
    execution_id: str
    execution_mode: str
    prepared: PreparedPrompt = field(repr=False)
    usage: RequestRecord = field(repr=False)
    content: AnswerContent = field(repr=False)
    evaluation_rubric: dict | None = field(default=None, repr=False)

    @property
    def status(self):
        return 'succeeded' if self.usage.success else 'failed'

    def safe_metadata(self):
        usage = self.usage.successful_response_usage
        return {
            'schema_version': 2 if self.evaluation_rubric else 1,
            **({'evaluation_rubric': self.evaluation_rubric} if self.evaluation_rubric else {}),
            'execution_id': self.execution_id,
            'execution_mode': self.execution_mode,
            'simulated': self.execution_mode == 'simulated',
            **self.prepared.safe_metadata(),
            'generation_settings': {
                'temperature': self.prepared.request.temperature,
                'max_output_tokens': self.prepared.request.max_output_tokens,
            },
            'provider': self.usage.provider,
            'model': self.usage.model,
            'status': self.status,
            'error_category': self.usage.error_category,
            'error_origin': self.usage.error_origin,
            'input_tokens': usage.input_tokens if usage else None,
            'output_tokens': usage.output_tokens if usage else None,
            'total_tokens': usage.total_tokens if usage else None,
            'latency_ms': self.usage.latency_ms,
            'attempt_count': self.usage.attempt_count,
            'estimated_cost_usd': (str(self.usage.successful_response_estimated_cost_usd)
                                   if self.usage.successful_response_estimated_cost_usd is not None else None),
            'llm': self.usage.to_dict(),
        }


class FixedContextRunner:
    """Accept cases returned by load_test_cases(); do not infer scoring labels.

    Dataset/schema validation remains the loader's responsibility. The runner
    validates its execution boundary and rejects a supplied package from another
    question/case/source selection before calling the shared client.
    """
    def __init__(self, client: LLMClient, sources: VerifiedSources | None = None, *, defense):
        self.client = client
        self.sources = sources
        self.defense = defense

    def run(self, case: dict, *, evidence: EvidencePackage | None = None,
            temperature: float | None = None, max_output_tokens: int | None = None) -> BaselineExecution:
        if (not isinstance(case, dict) or not isinstance(case.get('test_id'), str)
                or not re.fullmatch(r'E[0-9]{3}', case['test_id'])
                or not isinstance(case.get('question'), str) or not case['question'].strip()
                or case.get('evidence_mode') != 'fixed_context'
                or not isinstance(case.get('document_ids'), list) or not case['document_ids']
                or any(not isinstance(item, str) or not re.fullmatch(r'D[0-9]{3}', item)
                       for item in case['document_ids'])):
            raise PromptPreparationError('Expected a validated fixed-context test case')
        if evidence is None:
            if self.sources is None:
                self.sources = load_verified_sources()
            evidence = build_evidence(case, self.sources)
        if (not isinstance(evidence, EvidencePackage) or evidence.test_id != case['test_id']
                or evidence.question != case['question'] or evidence.document_ids != tuple(case['document_ids'])
                or evidence.evidence_mode != case['evidence_mode']):
            raise PromptPreparationError('Evidence does not match the selected test case')
        expected_hash = case.get('supporting_document_sha256')
        if expected_hash:
            supporting = next((doc for doc in evidence.documents
                               if doc.document_id == case.get('expected_answer_supported_by_document')), None)
            if supporting is None or supporting.sha256 != expected_hash:
                raise PromptPreparationError('Evidence does not match the supporting source hash')
        evaluation_rubric = legacy_rubric_for_case(case)
        try:
            result = self.defense.run(evidence, self.client, temperature=temperature,
                                      max_output_tokens=max_output_tokens)
            prepared, record, answer = result.prepared, result.completion.record, result.completion.text
        except DefenseExecutionError as exc:
            prepared, record, answer = exc.prepared, exc.record, None
        simulated = (self.client.config.provider == 'fake' or isinstance(self.client.adapter, FakeAdapter)
                     or any(attempt.usage is not None and attempt.usage.source == 'fake'
                            for attempt in record.attempts))
        candidates = tuple(CitationCandidate(
            document_id=match.group(), start_char=match.start(), end_char=match.end(),
            in_supplied_evidence=match.group() in evidence.document_ids,
        ) for match in DOCUMENT_MENTION.finditer(answer or ''))
        return BaselineExecution(
            execution_id=str(uuid4()), execution_mode='simulated' if simulated else 'real',
            prepared=prepared, usage=record,
            content=AnswerContent(case['question'], answer, candidates),
            evaluation_rubric=evaluation_rubric,
        )


class BaselineRunner(FixedContextRunner):
    """Configuration A using the shared execution and recording schema."""
    def __init__(self, client: LLMClient, sources: VerifiedSources | None = None):
        super().__init__(client, sources, defense=BaselineDefense())


def save_execution(execution: BaselineExecution, output_directory: str | Path) -> Path:
    """Save two exclusive 0600 files inside a fresh 0700 UUID directory.

    The output location is trusted operator input, never model/document content.
    No question, answer, citation text or test ID is used to construct a path.
    Ordinary recording failures remove the partial directory. Storage outages or
    process termination may still require orphan cleanup.
    """
    output = Path(output_directory)
    output.mkdir(parents=True, exist_ok=True, mode=0o700)
    if output.is_symlink() or not output.is_dir():
        raise ValueError('Output directory must be a regular directory')
    target = output / str(uuid4())
    target.mkdir(mode=0o700)  # Exclusive; never overwrite another execution.
    try:
        for name, payload in [('metadata.json', execution.safe_metadata()),
                              ('untrusted_content.json', asdict(execution.content))]:
            fd = os.open(target / name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
            with os.fdopen(fd, 'w', encoding='utf-8') as file:
                json.dump(payload, file, ensure_ascii=True, indent=2, allow_nan=False)
                file.write('\n')
    except BaseException:
        shutil.rmtree(target)
        raise
    return target
