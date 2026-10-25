"""OpenRouter transport restricted to the configured free Nemotron model."""
import json
from types import SimpleNamespace
import httpx

from app.core.config import OPENROUTER_MODEL
from app.llm.experiment_settings import MAX_COMPLETION_TOKENS


class OpenRouterStatusError(Exception):
    def __init__(self, response):
        super().__init__('OpenRouter returned an HTTP error')
        self.status_code = response.status_code
        self.response = response
        self.body = None
        try:
            value = response.json()
            if isinstance(value, dict):
                self.body = value
        except ValueError:
            pass


def generate(prompt, schema, config, observe_request, observe_response, *, max_output_tokens=MAX_COMPLETION_TOKENS):
    if config.provider != 'openrouter' or config.model != OPENROUTER_MODEL:
        raise ValueError('Only the configured free OpenRouter model is allowed')
    if config.base_url != 'https://openrouter.ai/api/v1':
        raise ValueError('Unexpected OpenRouter destination')

    # The free endpoint currently does not advertise structured-output support.
    schema_instruction = (
        'Return only one JSON object that conforms to this JSON Schema. '
        'Do not include Markdown fences or prose outside the JSON object:\n'
        + json.dumps(schema, ensure_ascii=False, sort_keys=True)
    )
    messages = []
    for message in prompt:
        role = 'system' if message.type == 'system' else 'user'
        content = message.content
        if role == 'system':
            content = content + '\n\n' + schema_instruction
        messages.append({'role': role, 'content': content})
    if not messages or messages[0]['role'] != 'system':
        messages.insert(0, {'role': 'system', 'content': schema_instruction})

    payload = {
        'model': OPENROUTER_MODEL,
        'messages': messages,
        'max_tokens': max_output_tokens,
        'stream': False,
        'provider': {'only': ['Nvidia'], 'allow_fallbacks': False},
    }
    with httpx.Client(
        timeout=config.request_timeout_seconds,
        follow_redirects=False,
        transport=httpx.HTTPTransport(retries=0),
        event_hooks={'request': [observe_request], 'response': [observe_response]},
    ) as transport:
        response = transport.post(
            config.base_url + '/chat/completions',
            json=payload,
            headers={'Authorization': f'Bearer {config.api_key}'},
        )
        if response.status_code != 200:
            raise OpenRouterStatusError(response)
        body = response.json()

    usage = body.get('usage')
    normalized = None
    if isinstance(usage, dict):
        fields = ('prompt_tokens', 'completion_tokens', 'total_tokens')
        if all(type(usage.get(name)) is int and usage[name] >= 0 for name in fields):
            normalized = {'input_tokens': usage['prompt_tokens'],
                          'output_tokens': usage['completion_tokens'],
                          'total_tokens': usage['total_tokens']}
    choice = body['choices'][0]
    finish = choice.get('finish_reason')
    return SimpleNamespace(
        content=choice['message'].get('content'),
        usage_metadata=normalized,
        response_metadata={},
        id=body.get('id'),
        finish_reason=finish if finish in {'stop', 'length', 'tool_calls', 'content_filter'} else None,
    )
