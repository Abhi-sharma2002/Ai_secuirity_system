"""Offline Phase 4 example: fake usage and artificial pricing, never live I/O."""
import json
from decimal import Decimal

from app.core.logging import configure_logging
from legacy_llm.client import LLMClient, ProviderError, ProviderResponse
from legacy_llm.fake import FakeAdapter
from legacy_llm.models import LLMConfig, LLMRequest, Message
from legacy_llm.usage import Pricing, TokenUsage


def main():
    configure_logging()
    # Explicit fake config: provider environment variables cannot turn this into
    # a paid call. Counts and prices below are scripted demonstration data.
    adapter = FakeAdapter([
        ProviderError('rate_limit', retry_after_s=0),
        ProviderResponse('Scripted answer; no real LLM was called.', TokenUsage(120, 30)),
    ])
    client = LLMClient(
        LLMConfig(backoff_initial_s=0.01), adapter,
        pricing=Pricing('fake', 'fake-model', 'demo-artificial-v1', Decimal('1'), Decimal('2')),
    )
    result = client.complete(LLMRequest(
        messages=(Message('user', 'Demonstrate usage tracking.'),),
        test_id='demo-001', configuration_id='demo',
    ))
    print('FAKE ONLY: scripted token counts and artificial rates; no provider API was called.')
    print(json.dumps(result.record.to_dict(), indent=2))
    print('Retried-attempt usage is unknown, so complete usage and cost totals remain unknown.')


if __name__ == '__main__':
    main()
