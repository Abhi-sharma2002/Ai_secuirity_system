"""Shared call/retry boundary. Only injected adapters can perform provider I/O."""
import logging
import os
import time
from dataclasses import dataclass, field
from typing import Protocol
from uuid import uuid4

from legacy_llm.models import (
    ConfigurationError, LLMConfig, LLMRequest, ProviderCapabilities,
    RequestValidationError, finite_number,
)
from legacy_llm.usage import AttemptRecord, Pricing, RequestRecord, TokenUsage, UsageTracker

logger = logging.getLogger(__name__)
PROVIDER_ERRORS = frozenset({'timeout', 'rate_limit', 'transient', 'authentication',
                             'invalid_request', 'permission', 'invalid_response'})
RETRYABLE = frozenset({'timeout', 'rate_limit', 'transient'})


class ProviderError(Exception):
    """Adapter-normalized error. Never include raw HTTP bodies, headers or SDK errors.

    retry_after_s is the adapter's parsed Retry-After/reset guidance in seconds.
    billed_usage is set only when explicitly reported as billed by the provider.
    """
    def __init__(self, category: str, *, retry_after_s: float | None = None,
                 usage: TokenUsage | None = None, billed_usage: TokenUsage | None = None):
        if category not in PROVIDER_ERRORS:
            raise ValueError('Unknown provider error category')
        if retry_after_s is not None and not finite_number(retry_after_s):
            raise ValueError('Invalid retry guidance')
        if any(value is not None and not isinstance(value, TokenUsage) for value in (usage, billed_usage)):
            raise ValueError('Invalid provider error usage')
        self.category = category
        self.retry_after_s = retry_after_s
        self.usage = usage
        self.billed_usage = billed_usage
        super().__init__(f'LLM provider error: {category}')


@dataclass(frozen=True)
class ProviderResponse:
    text: str = field(repr=False)
    usage: TokenUsage | None = None
    billed_usage: TokenUsage | None = None

    def __post_init__(self):
        if not isinstance(self.text, str):
            raise ValueError('Provider response text must be a string')
        if any(value is not None and not isinstance(value, TokenUsage) for value in (self.usage, self.billed_usage)):
            raise ValueError('Invalid provider response usage')


class ProviderAdapter(Protocol):
    provider: str
    capabilities: ProviderCapabilities
    requires_credentials: bool

    def generate(self, request: LLMRequest, *, model: str, credential: str | None,
                 connect_timeout_s: float, request_timeout_s: float) -> ProviderResponse:
        """Honor both timeouts; disable SDK retries, tools, and raw request logging.

        Capabilities must describe the configured model/API, not just the vendor.
        Preserve role boundaries and raw content. Normalize errors to ProviderError.
        """
        ...


@dataclass(frozen=True)
class LLMResult:
    text: str = field(repr=False)
    record: RequestRecord


class LLMRequestError(RuntimeError):
    """Terminal provider/application failure with a content-free experiment record."""
    def __init__(self, record: RequestRecord):
        self.record = record
        super().__init__(f'LLM request failed: {record.error_origin}/{record.error_category}')


class LLMClient:
    def __init__(self, config: LLMConfig, adapter: ProviderAdapter, *, pricing: Pricing | None = None,
                 tracker: UsageTracker | None = None, clock=time.perf_counter, sleep=time.sleep):
        if not isinstance(config, LLMConfig):
            raise ConfigurationError('Expected LLMConfig')
        if (getattr(adapter, 'provider', None) != config.provider
                or not isinstance(getattr(adapter, 'capabilities', None), ProviderCapabilities)
                or type(getattr(adapter, 'requires_credentials', None)) is not bool):
            raise ConfigurationError('Adapter does not match provider configuration')
        if pricing is not None and (not isinstance(pricing, Pricing)
                                    or (pricing.provider, pricing.model) != (config.provider, config.model)):
            raise ConfigurationError('Pricing does not match provider/model')
        self._credential = load_credential(config) if adapter.requires_credentials else None
        self.config = config
        self.adapter = adapter
        self.pricing = pricing
        self.tracker = tracker if tracker is not None else UsageTracker()
        self._clock, self._sleep = clock, sleep

    def complete(self, request: LLMRequest) -> LLMResult:
        if not isinstance(request, LLMRequest):
            raise RequestValidationError('Expected LLMRequest')
        self.adapter.capabilities.validate(request)
        request_id = str(uuid4())
        started = self._clock()
        attempts = []
        response = None
        for number in range(1, self.config.max_retries + 2):
            attempt_started = self._clock()
            category = origin = None
            usage = billed_usage = None
            retry_after = None
            try:
                response = self.adapter.generate(
                    request, model=self.config.model, credential=self._credential,
                    connect_timeout_s=self.config.connect_timeout_s,
                    request_timeout_s=self.config.request_timeout_s,
                )
                if not isinstance(response, ProviderResponse):
                    raise ProviderError('invalid_response')
                usage, billed_usage = response.usage, response.billed_usage
            except ProviderError as exc:
                category, origin = exc.category, 'provider'
                usage, billed_usage = exc.usage, exc.billed_usage
                retry_after = exc.retry_after_s
            except TimeoutError:
                category, origin = 'timeout', 'provider'
            except ConnectionError:
                category, origin = 'transient', 'provider'
            except Exception:
                # Programming errors are not provider outages and must not retry.
                # Discard raw exceptions, which can contain credentials/prompts.
                category, origin = 'application_error', 'application'
            elapsed = max(0.0, (self._clock() - attempt_started) * 1000)
            delay = None
            if category in RETRYABLE and number <= self.config.max_retries:
                candidate = min(self.config.backoff_initial_s * 2 ** (number - 1),
                                self.config.max_retry_delay_s)
                if retry_after is not None:
                    candidate = max(candidate, retry_after)
                # Never retry earlier than provider guidance to meet a local cap.
                # Fail now if the required wait exceeds the configured wait budget.
                if candidate <= self.config.max_retry_delay_s:
                    delay = candidate
            attempts.append(AttemptRecord(
                attempt=number, latency_ms=elapsed, success=category is None,
                error_category=category, error_origin=origin, usage=usage, billed_usage=billed_usage,
                estimated_cost_usd=self.pricing.estimate(usage) if self.pricing else None,
                retry_delay_ms=delay * 1000 if delay is not None else None,
            ))
            # Allowlisted fields only: no exception strings, messages, evidence,
            # generated text, credentials, endpoints or arbitrary provider IDs.
            logger.info('llm_attempt request_id=%s attempt=%d success=%s error_category=%s latency_ms=%.3f',
                        request_id, number, category is None, category, elapsed)
            if delay is None:
                break
            self._sleep(delay)
        last = attempts[-1]
        record = RequestRecord(
            request_id=request_id, test_id=request.test_id, configuration_id=request.configuration_id,
            evidence_fingerprint=request.evidence_fingerprint,
            provider=self.config.provider, model=self.config.model,
            latency_ms=max(0.0, (self._clock() - started) * 1000),
            success=last.success, error_category=last.error_category, error_origin=last.error_origin,
            attempts=tuple(attempts), pricing=self.pricing,
        )
        self.tracker.record(record)
        logger.info('llm_request request_id=%s attempts=%d success=%s latency_ms=%.3f',
                    request_id, len(attempts), record.success, record.latency_ms)
        if not record.success:
            raise LLMRequestError(record) from None
        return LLMResult(response.text, record)


def load_credential(config: LLMConfig) -> str:
    credential = os.getenv(config.credential_env)
    if not credential or not credential.strip():
        raise ConfigurationError('Required provider credential is missing from the configured environment variable')
    return credential


def create_client(config: LLMConfig | None = None, *, adapter: ProviderAdapter | None = None,
                  pricing: Pricing | None = None, tracker: UsageTracker | None = None) -> LLMClient:
    config = config if config is not None else LLMConfig.from_env()
    if not isinstance(config, LLMConfig):
        raise ConfigurationError('Expected LLMConfig')
    if adapter is None:
        if config.provider != 'fake':
            load_credential(config)  # fail clearly on missing secrets before adapter setup
            raise ConfigurationError('No approved live provider adapter is installed; inject a reviewed adapter')
        from legacy_llm.fake import FakeAdapter
        adapter = FakeAdapter()
    if pricing is None:
        pricing = Pricing.from_env(config.provider, config.model)
    return LLMClient(config, adapter, pricing=pricing, tracker=tracker)
