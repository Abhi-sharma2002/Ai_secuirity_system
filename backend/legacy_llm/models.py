"""Validated value objects shared by provider adapters and experiment callers."""
import math
import os
import re
from dataclasses import dataclass, field
from typing import Literal


class ConfigurationError(ValueError):
    """Configuration cannot be used; messages never include environment values."""


class RequestValidationError(ValueError):
    """Application input or requested capabilities are invalid; no call was made."""


def finite_number(value, *, positive=False):
    return (type(value) in (int, float) and math.isfinite(value)
            and (value > 0 if positive else value >= 0))


def identifier(value):
    return isinstance(value, str) and re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.:/-]{0,199}', value) is not None


@dataclass(frozen=True)
class LLMConfig:
    provider: str = 'fake'
    model: str = 'fake-model'
    connect_timeout_s: float = 5.0
    request_timeout_s: float = 30.0
    max_retries: int = 2
    backoff_initial_s: float = 0.5
    max_retry_delay_s: float = 30.0
    credential_env: str = 'LLM_API_KEY'

    def __post_init__(self):
        if not identifier(self.provider) or not identifier(self.model):
            raise ConfigurationError('Provider and model must be nonempty identifiers')
        if self.provider != 'fake' and self.model == 'fake-model':
            raise ConfigurationError('A live provider requires an explicit approved model identifier')
        for name in ('connect_timeout_s', 'request_timeout_s', 'backoff_initial_s', 'max_retry_delay_s'):
            if not finite_number(getattr(self, name), positive=True):
                raise ConfigurationError('Timeouts and retry delays must be finite positive numbers')
        if self.connect_timeout_s > self.request_timeout_s:
            raise ConfigurationError('Connection timeout cannot exceed request timeout')
        if self.backoff_initial_s > self.max_retry_delay_s:
            raise ConfigurationError('Initial backoff cannot exceed maximum retry delay')
        if type(self.max_retries) is not int or not 0 <= self.max_retries <= 10:
            raise ConfigurationError('max_retries must be an integer between 0 and 10')
        if not isinstance(self.credential_env, str) or not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', self.credential_env):
            raise ConfigurationError('Invalid credential environment variable name')

    @classmethod
    def from_env(cls):
        try:
            return cls(
                provider=os.getenv('LLM_PROVIDER', 'fake'), model=os.getenv('LLM_MODEL', 'fake-model'),
                connect_timeout_s=float(os.getenv('LLM_CONNECT_TIMEOUT_SECONDS', '5')),
                request_timeout_s=float(os.getenv('LLM_REQUEST_TIMEOUT_SECONDS', '30')),
                max_retries=int(os.getenv('LLM_MAX_RETRIES', '2')),
                backoff_initial_s=float(os.getenv('LLM_BACKOFF_INITIAL_SECONDS', '0.5')),
                max_retry_delay_s=float(os.getenv('LLM_MAX_RETRY_DELAY_SECONDS', '30')),
                credential_env=os.getenv('LLM_CREDENTIAL_ENV', 'LLM_API_KEY'),
            )
        except (TypeError, ValueError):
            raise ConfigurationError('Invalid LLM environment configuration') from None


Role = Literal['system', 'developer', 'user', 'assistant']


@dataclass(frozen=True)
class Message:
    role: Role
    content: str = field(repr=False)
    untrusted: bool = False

    def __post_init__(self):
        if self.role not in ('system', 'developer', 'user', 'assistant'):
            raise RequestValidationError('Unsupported message role')
        if not isinstance(self.content, str) or not self.content.strip():
            raise RequestValidationError('Message content must be nonempty text')
        try:
            self.content.encode('utf-8')
        except UnicodeError:
            raise RequestValidationError('Message must be valid UTF-8 text') from None
        if type(self.untrusted) is not bool or (self.untrusted and self.role != 'user'):
            raise RequestValidationError('Untrusted evidence must remain in a user message')


@dataclass(frozen=True)
class LLMRequest:
    messages: tuple[Message, ...] = field(repr=False)
    temperature: float | None = None
    max_output_tokens: int | None = None
    test_id: str | None = None
    configuration_id: str | None = None
    evidence_fingerprint: str | None = None

    def __post_init__(self):
        if not isinstance(self.messages, tuple) or not self.messages or any(
            not isinstance(message, Message) for message in self.messages
        ):
            raise RequestValidationError('Messages must be a nonempty tuple of Message objects')
        if self.temperature is not None and not finite_number(self.temperature):
            raise RequestValidationError('Temperature must be a finite nonnegative number')
        if self.max_output_tokens is not None and (
            type(self.max_output_tokens) is not int or self.max_output_tokens <= 0
        ):
            raise RequestValidationError('max_output_tokens must be a positive integer')
        for value in (self.test_id, self.configuration_id):
            if value is not None and not identifier(value):
                raise RequestValidationError('Invalid experiment identifier')
        if self.evidence_fingerprint is not None and (
            not isinstance(self.evidence_fingerprint, str)
            or not re.fullmatch(r'[0-9a-f]{64}', self.evidence_fingerprint)
        ):
            raise RequestValidationError('Invalid evidence fingerprint')


@dataclass(frozen=True)
class ProviderCapabilities:
    roles: frozenset[str]
    temperature_range: tuple[float, float] | None = None
    max_output_tokens: int | None = None

    def __post_init__(self):
        if not isinstance(self.roles, frozenset) or not self.roles or not self.roles <= {
            'system', 'developer', 'user', 'assistant'
        }:
            raise ConfigurationError('Invalid provider message capabilities')
        if self.temperature_range is not None:
            bounds = self.temperature_range
            if (not isinstance(bounds, tuple) or len(bounds) != 2
                    or not all(finite_number(v) for v in bounds) or bounds[0] > bounds[1]):
                raise ConfigurationError('Invalid provider temperature capabilities')
        if self.max_output_tokens is not None and (
            type(self.max_output_tokens) is not int or self.max_output_tokens <= 0
        ):
            raise ConfigurationError('Invalid provider output-token capability')

    def validate(self, request: LLMRequest):
        if any(message.role not in self.roles for message in request.messages):
            raise RequestValidationError('Provider does not support a requested role; roles are never remapped')
        if request.temperature is not None and (
            self.temperature_range is None
            or not self.temperature_range[0] <= request.temperature <= self.temperature_range[1]
        ):
            raise RequestValidationError('Provider does not support the requested temperature')
        if request.max_output_tokens is not None and (
            self.max_output_tokens is None or request.max_output_tokens > self.max_output_tokens
        ):
            raise RequestValidationError('Provider does not support the requested output-token setting')
