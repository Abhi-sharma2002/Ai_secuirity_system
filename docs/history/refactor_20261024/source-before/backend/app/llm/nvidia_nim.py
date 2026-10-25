"""Hosted NVIDIA / self-hosted NIM transport. No retries, polling or fallback."""
import ssl
import os
from types import SimpleNamespace
import httpx


class NIMStatusError(Exception):
    def __init__(self, response):
        super().__init__('NIM returned an HTTP error')
        self.status_code = response.status_code
        self.response = response
        self.body = None
        try:
            value = response.json()
            if isinstance(value, dict):
                self.body = value
        except ValueError:
            pass


def generate(prompt, schema, config, observe_request, observe_response):
    headers = {}
    if config.auth_mode == 'bearer':
        headers['Authorization'] = 'Bearer '+config.api_key
    ca_file = os.getenv('NVIDIA_CA_FILE', '').strip()
    # Keep TLS verification and normal proxy/environment behavior enabled.
    verify = ssl.create_default_context(cafile=ca_file) if ca_file else True
    payload = {'model': config.model, 'messages': [
        {'role': 'system' if m.type == 'system' else 'user', 'content': m.content} for m in prompt],
        'temperature': 1.0, 'max_tokens': 700, 'stream': False,
        'response_format': {'type': 'json_schema', 'json_schema': {
            'name': schema.get('title', 'security_response'), 'strict': True, 'schema': schema}}}
    if config.reasoning_effort:
        payload['reasoning_effort'] = config.reasoning_effort
    with httpx.Client(timeout=config.request_timeout_seconds, follow_redirects=False, verify=verify,
                      event_hooks={'request':[observe_request], 'response':[observe_response]}) as transport:
        response = transport.post(config.base_url+'/chat/completions', json=payload, headers=headers)
        if response.status_code != 200:
            raise NIMStatusError(response)
        body = response.json()
    usage = body.get('usage')
    normalized = None
    if isinstance(usage, dict):
        names = {'input_tokens':'prompt_tokens','output_tokens':'completion_tokens','total_tokens':'total_tokens'}
        if all(type(usage.get(source)) is int and usage[source] >= 0 for source in names.values()):
            normalized = {target:usage[source] for target,source in names.items()}
    choice = body['choices'][0]
    finish = choice.get('finish_reason')
    return SimpleNamespace(content=choice['message'].get('content'), usage_metadata=normalized,
                           response_metadata={}, id=body.get('id'),
                           finish_reason=finish if finish in {'stop','length','tool_calls','content_filter'} else None)
