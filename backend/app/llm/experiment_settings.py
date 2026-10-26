"""Approved Azure gpt-5-mini settings revision; never a frozen execution identity."""
VERSION = 'azure-gpt5mini-v4-shared-minimal-reasoning'
# Historical OpenRouter default; Azure reads its cap from the shared YAML below.
MAX_COMPLETION_TOKENS = 700


def identity_settings():
    from app.evaluation.simple_config import load_config
    config = load_config()
    return {'configuration_version': VERSION, 'temperature': 'not sent',
            'provider_seed': 'not sent', 'max_output_tokens': config['max_tokens'],
            'reasoning_effort': config['reasoning_effort'],
            'max_retries': 0}
