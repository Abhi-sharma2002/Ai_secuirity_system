"""Content-free attempt accounting. None means unknown, never an estimated token count."""
import os
from dataclasses import asdict, dataclass
from decimal import Decimal, InvalidOperation
from threading import Lock

from legacy_llm.models import ConfigurationError, identifier


@dataclass(frozen=True)
class TokenUsage:
    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None
    source: str = 'provider'

    def __post_init__(self):
        for count in (self.input_tokens, self.output_tokens, self.total_tokens):
            if count is not None and (type(count) is not int or count < 0):
                raise ValueError('Token counts must be nonnegative integers or unknown')
        if self.source not in {'provider', 'fake'}:
            raise ValueError('Only provider-reported or explicitly fake usage is supported')
        if self.input_tokens is not None and self.output_tokens is not None:
            total = self.input_tokens + self.output_tokens
            if self.total_tokens is None:
                object.__setattr__(self, 'total_tokens', total)
            elif total != self.total_tokens:
                raise ValueError('Inconsistent token totals')
        elif self.total_tokens is not None and any(
            value is not None and value > self.total_tokens for value in (self.input_tokens, self.output_tokens)
        ):
            raise ValueError('Inconsistent partial token totals')


def sum_usage(items: list[TokenUsage | None]) -> TokenUsage | None:
    if not items or any(item is None for item in items):
        return None
    def total(field):
        counts = [getattr(item, field) for item in items]
        return None if any(value is None for value in counts) else sum(counts)
    return TokenUsage(total('input_tokens'), total('output_tokens'), total('total_tokens'),
                      source='fake' if any(item.source == 'fake' for item in items) else 'provider')


@dataclass(frozen=True)
class Pricing:
    provider: str
    model: str
    version: str
    input_usd_per_million: Decimal
    output_usd_per_million: Decimal

    def __post_init__(self):
        if not all(identifier(value) for value in (self.provider, self.model, self.version)):
            raise ConfigurationError('Pricing requires provider, model, and version identifiers')
        for value in (self.input_usd_per_million, self.output_usd_per_million):
            if not isinstance(value, Decimal) or not value.is_finite() or value < 0:
                raise ConfigurationError('Pricing rates must be finite nonnegative Decimals')

    @classmethod
    def from_env(cls, provider: str, model: str):
        values = [os.getenv(key) for key in (
            'LLM_PRICING_VERSION', 'LLM_INPUT_USD_PER_MILLION', 'LLM_OUTPUT_USD_PER_MILLION')]
        if all(value is None for value in values):
            return None
        if any(value is None or not value.strip() for value in values):
            raise ConfigurationError('Pricing requires a version and both USD rates')
        try:
            return cls(provider, model, values[0], Decimal(values[1]), Decimal(values[2]))
        except (ValueError, InvalidOperation):
            raise ConfigurationError('Invalid pricing environment configuration') from None

    def estimate(self, usage: TokenUsage | None) -> Decimal | None:
        if usage is None or usage.input_tokens is None or usage.output_tokens is None:
            return None
        return (usage.input_tokens * self.input_usd_per_million
                + usage.output_tokens * self.output_usd_per_million) / Decimal(1_000_000)


@dataclass(frozen=True)
class AttemptRecord:
    attempt: int
    latency_ms: float
    success: bool
    error_category: str | None
    error_origin: str | None
    usage: TokenUsage | None
    billed_usage: TokenUsage | None
    estimated_cost_usd: Decimal | None
    retry_delay_ms: float | None = None


@dataclass(frozen=True)
class RequestRecord:
    request_id: str
    test_id: str | None
    configuration_id: str | None
    evidence_fingerprint: str | None
    provider: str
    model: str
    latency_ms: float
    success: bool
    error_category: str | None
    error_origin: str | None
    attempts: tuple[AttemptRecord, ...]
    pricing: Pricing | None

    @property
    def attempt_count(self):
        return len(self.attempts)

    @property
    def successful_response_usage(self):
        return self.attempts[-1].usage if self.success else None

    @property
    def total_reported_usage(self):
        """Unknown if any attempt lacks usage; never assume failed attempts are free."""
        return sum_usage([attempt.usage for attempt in self.attempts])

    @property
    def known_reported_usage(self):
        """Sum only observed attempts. Not a claim about complete/billed usage."""
        return sum_usage([attempt.usage for attempt in self.attempts if attempt.usage is not None])

    @property
    def total_billed_usage(self):
        return sum_usage([attempt.billed_usage for attempt in self.attempts])

    @property
    def successful_response_estimated_cost_usd(self):
        return self.attempts[-1].estimated_cost_usd if self.success else None

    @property
    def total_estimated_cost_usd(self):
        costs = [attempt.estimated_cost_usd for attempt in self.attempts]
        return None if not costs or any(cost is None for cost in costs) else sum(costs, Decimal(0))

    @property
    def known_attempts_estimated_cost_usd(self):
        costs = [attempt.estimated_cost_usd for attempt in self.attempts if attempt.estimated_cost_usd is not None]
        return sum(costs, Decimal(0)) if costs else None

    @property
    def total_billed_estimated_cost_usd(self):
        return self.pricing.estimate(self.total_billed_usage) if self.pricing else None

    def to_dict(self):
        """JSON-friendly metadata only. Decimal money values retain exact precision."""
        record = asdict(self)
        record.update(attempt_count=self.attempt_count,
                      successful_response_usage=self.successful_response_usage,
                      total_reported_usage=self.total_reported_usage,
                      known_reported_usage=self.known_reported_usage,
                      total_billed_usage=self.total_billed_usage,
                      successful_response_estimated_cost_usd=self.successful_response_estimated_cost_usd,
                      total_estimated_cost_usd=self.total_estimated_cost_usd,
                      known_attempts_estimated_cost_usd=self.known_attempts_estimated_cost_usd,
                      total_billed_estimated_cost_usd=self.total_billed_estimated_cost_usd)
        def encode(value):
            if isinstance(value, Decimal):
                return str(value)
            if isinstance(value, TokenUsage):
                return asdict(value)
            if isinstance(value, dict):
                return {key: encode(item) for key, item in value.items()}
            if isinstance(value, (list, tuple)):
                return [encode(item) for item in value]
            return value
        return encode(record)


class UsageTracker:
    """Explicit in-memory collector; caller controls export and retention."""
    def __init__(self):
        self._records = []
        self._lock = Lock()

    def record(self, record: RequestRecord):
        with self._lock:
            self._records.append(record)

    def snapshot(self) -> tuple[RequestRecord, ...]:
        with self._lock:
            return tuple(self._records)
