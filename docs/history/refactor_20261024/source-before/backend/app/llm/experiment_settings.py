"""Approved Azure gpt-5-mini settings revision; never a frozen execution identity."""
VERSION = 'azure-gpt5mini-v2-temperature-not-sent'
MAX_COMPLETION_TOKENS = 700


def identity_settings():
    return {'configuration_version': VERSION, 'temperature': 'not sent',
            'provider_seed': 'not sent', 'max_output_tokens': MAX_COMPLETION_TOKENS,
            'max_retries': 0}
