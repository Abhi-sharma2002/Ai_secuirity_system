"""Scripted, credential-free test adapter. Never imports an SDK or opens a socket."""
from dataclasses import replace
from threading import Lock

from legacy_llm.client import ProviderError, ProviderResponse
from legacy_llm.models import ProviderCapabilities


class FakeAdapter:
    provider = 'fake'
    requires_credentials = False
    capabilities = ProviderCapabilities(frozenset({'system', 'developer', 'user', 'assistant'}),
                                        temperature_range=(0.0, 2.0), max_output_tokens=4096)

    def __init__(self, events=None):
        self._events = list(events) if events is not None else [ProviderResponse('Fake response; no network call.')]
        self._lock = Lock()
        self.calls = []  # Tests only; this adapter retains requests in memory, never logs them.

    def generate(self, request, **options):
        with self._lock:
            self.calls.append((request, options))
            if not self._events:
                raise RuntimeError('Fake adapter has no remaining scripted response')
            event = self._events.pop(0)
        def fake_usage(usage):
            return replace(usage, source='fake') if usage is not None else None
        if isinstance(event, ProviderError):
            raise ProviderError(event.category, retry_after_s=event.retry_after_s,
                                usage=fake_usage(event.usage), billed_usage=fake_usage(event.billed_usage))
        if isinstance(event, Exception):
            raise event
        if isinstance(event, ProviderResponse):
            return replace(event, usage=fake_usage(event.usage), billed_usage=fake_usage(event.billed_usage))
        return event  # Allows invalid-provider-response contract tests.
