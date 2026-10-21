"""Configuration B smoke test. Fake by default; explicit opt-in for live execution."""
import argparse
import json
import sys
from pathlib import Path

from app.core.config import ROOT
from app.core.logging import configure_logging
from app.defenses.base import PromptPreparationError
from app.defenses.baseline_runner import save_execution
from app.defenses.instruction_separation_runner import InstructionSeparationRunner
from app.evaluation.evidence_builder import EvidenceBuildError, load_verified_sources
from app.evaluation.test_case_loader import load_test_cases, TestCaseValidationError
from legacy_llm.client import LLMClient, ProviderResponse, create_client
from legacy_llm.fake import FakeAdapter
from legacy_llm.models import ConfigurationError, LLMConfig, RequestValidationError

DEFAULT_OUTPUT = ROOT.parent / 'results' / 'instruction_separation'


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--test-id', required=True, help='Validated case ID, e.g. E001')
    parser.add_argument('--output-dir', type=Path, default=DEFAULT_OUTPUT,
                        help='Private result location (default: project results/instruction_separation)')
    parser.add_argument('--allow-live', action='store_true',
                        help='Explicit opt-in; requires an approved configured non-fake provider adapter')
    parser.add_argument('--temperature', type=float, default=None)
    parser.add_argument('--max-output-tokens', type=int, default=None)
    args = parser.parse_args(argv)
    configure_logging()
    try:
        cases = load_test_cases()
        case = next((case for case in cases if case['test_id'] == args.test_id), None)
        if case is None:
            print('FAIL: selected test ID was not found in the validated dataset', file=sys.stderr)
            return 2
        if args.allow_live:
            config = LLMConfig.from_env()
            if config.provider == 'fake':
                raise ConfigurationError('Live mode requires an approved non-fake provider configuration')
            client = create_client(config)  # Fails closed: no approved live adapter currently installed.
        else:
            client = LLMClient(LLMConfig(), FakeAdapter([
                ProviderResponse('SIMULATED instruction-separation response; not a real model answer or evaluation outcome.'),
            ]))
        execution = InstructionSeparationRunner(client, load_verified_sources()).run(
            case, temperature=args.temperature, max_output_tokens=args.max_output_tokens)
        saved = save_execution(execution, args.output_dir)
    except (ConfigurationError, RequestValidationError) as exc:
        # These shared exception types contain fixed, value-free diagnostics.
        print(f'FAIL: {exc}; no result recorded', file=sys.stderr)
        return 2
    except (PromptPreparationError, EvidenceBuildError, TestCaseValidationError):
        # Never echo raw provider exceptions, prompts, content, or secret settings.
        print('FAIL: configuration, case, evidence, or generation settings are invalid; no result recorded', file=sys.stderr)
        return 2
    except (OSError, ValueError):
        print('FAIL: could not record the execution result', file=sys.stderr)
        return 1
    metadata = execution.safe_metadata()
    print('SIMULATED — fake output; not eligible for real attack-success statistics.'
          if execution.execution_mode == 'simulated' else 'REAL — no scoring has been performed.')
    print(json.dumps({key: metadata[key] for key in (
        'test_id', 'configuration_id', 'execution_mode', 'provider', 'model', 'status',
        'input_tokens', 'output_tokens', 'total_tokens', 'latency_ms', 'attempt_count',
        'estimated_cost_usd', 'error_category', 'prompt_version', 'message_roles')}, indent=2))
    print(f'Results saved in: {saved}')
    return 0 if execution.status == 'succeeded' else 1


if __name__ == '__main__':
    raise SystemExit(main())
