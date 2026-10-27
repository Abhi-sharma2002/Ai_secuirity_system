"""Capture public execution/scoring inputs; no credentials or environment dumps."""
import hashlib
from pathlib import Path
from app.core.config import LiveSettings
from app.defenses import baseline, instruction_separation, screening, output_screening


def capture(prompt_hash):
    # Deferred import avoids runtime/evaluator import cycles; no evaluation runs.
    from app.evaluation.experiment import execution_identity
    config=LiveSettings.from_env()
    if config.provider == 'azure_openai':
        from app.llm.experiment_settings import identity_settings
        settings = {'provider': config.provider, 'api': 'azure_openai_v1_chat_completions', **identity_settings()}
        stages = {stage: dict(settings) for stage in ('generation', 'screening')}
        routing = {'allow_fallbacks': False}
    elif config.provider == 'openrouter':
        settings = {'provider': config.provider, 'api': 'openrouter_chat_completions',
                    'configuration_version': 'openrouter-nemotron-free-v2-answer1400',
                    'temperature': 'not sent', 'provider_seed': 'not sent', 'max_retries': 0}
        stages = {'generation': settings | {'max_output_tokens': 1400},
                  'screening': settings | {'max_output_tokens': 700}}
        routing = {'only': ['Nvidia'], 'allow_fallbacks': False}
    else:
        raise ValueError('Unsupported comparison provider')
    scoring=Path(__file__).resolve().parents[3]/'docs/SCORING.md'
    return {'version':'interactive-review-provenance-v1','provider':config.provider,'model':config.model,
            'endpoint':config.base_url+'/chat/completions', 'routing':routing,
            'request_timeout_seconds':config.request_timeout_seconds,
            'stage_settings':stages,
            'defense_versions':{m:{'grounding':baseline.PROMPT_VERSION,
                'separation':instruction_separation.PROMPT_VERSION if m in 'BC' else None,
                'output_screening':output_screening.VERSION if m=='C' else None} for m in 'ABC'},
            'screening_prompt_version':screening.PROMPT_VERSION,'prompt_hash':prompt_hash,
            'execution_identity':execution_identity(),'scoring_spec_hash':hashlib.sha256(scoring.read_bytes()).hexdigest(),
            'rubric_version':'human-v1','scoring_rules':{'version':'interactive-retrospective-human-v1',
                'population':'benign_interactive_not_controlled_benchmark',
                'quality_scale':[0,1,2,3,4],'criteria_timing':'expected answer supplied retrospectively at import'}}
