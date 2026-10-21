"""Offline Configuration A demonstration using real fixed-context evidence."""
import json

from app.core.logging import configure_logging
from app.defenses.baseline import BaselineDefense
from app.evaluation.evidence_builder import build_evidence, load_verified_sources
from app.evaluation.test_case_loader import load_test_cases
from legacy_llm.client import LLMClient, ProviderResponse
from legacy_llm.fake import FakeAdapter
from legacy_llm.models import LLMConfig


def main():
    configure_logging()
    case = load_test_cases()[0]
    package = build_evidence(case, load_verified_sources())
    client = LLMClient(LLMConfig(), FakeAdapter([
        ProviderResponse('Scripted baseline output; not a real answer or evaluation result.'),
    ]))
    result = BaselineDefense().run(package, client)
    print('FAKE ONLY: Configuration A wiring with real evidence; no model quality/security result.')
    print(json.dumps(result.safe_metadata(), indent=2))
    print('No live API call, screening, attack scoring, or tool execution occurred.')


if __name__ == '__main__':
    main()
