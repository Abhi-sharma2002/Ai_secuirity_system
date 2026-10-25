"""Azure OpenAI v1 Chat Completions. One HTTP attempt, strict schema, no fallback."""
from types import SimpleNamespace
import httpx
from app.llm.experiment_settings import MAX_COMPLETION_TOKENS


class AzureStatusError(Exception):
    def __init__(self, response):
        super().__init__('Azure OpenAI returned an HTTP error')
        self.status_code = response.status_code
        self.response = response
        self.body = None
        try:
            value = response.json()
            if isinstance(value, dict):
                self.body = value
        except ValueError:
            pass


def generate(prompt, schema, config, observe_request, observe_response, *, screening_reasoning_effort=None):
    if config.provider != 'azure_openai':
        raise ValueError('Historical provider routing is disabled')
    payload = {'model': config.model, 'messages': [
        {'role': 'system' if m.type == 'system' else 'user', 'content': m.content} for m in prompt],
        'max_completion_tokens': MAX_COMPLETION_TOKENS, 'stream': False,
        'response_format': {'type': 'json_schema', 'json_schema': {
            'name': schema.get('title', 'security_response'), 'strict': True, 'schema': schema}}}
    if screening_reasoning_effort is not None:
        if screening_reasoning_effort != 'minimal' or schema.get('title') != 'Screening':
            raise ValueError('Only the explicit minimal-screening revision is supported')
        payload['reasoning_effort'] = screening_reasoning_effort
    with httpx.Client(timeout=config.request_timeout_seconds, follow_redirects=False,
                      transport=httpx.HTTPTransport(retries=0),
                      event_hooks={'request': [observe_request], 'response': [observe_response]}) as transport:
        response = transport.post(config.base_url + '/chat/completions', json=payload,
                                  headers={'api-key': config.api_key})
        if response.status_code != 200:
            raise AzureStatusError(response)
        body = response.json()
    usage = body.get('usage')
    normalized = None
    if isinstance(usage, dict):
        names = {'input_tokens': 'prompt_tokens', 'output_tokens': 'completion_tokens', 'total_tokens': 'total_tokens'}
        if all(type(usage.get(source)) is int and usage[source] >= 0 for source in names.values()):
            normalized = {target: usage[source] for target, source in names.items()}
    choice = body['choices'][0]
    finish = choice.get('finish_reason')
    details = usage.get('completion_tokens_details') if isinstance(usage, dict) else None
    reasoning = details.get('reasoning_tokens') if isinstance(details, dict) else None
    metadata = {'reasoning_tokens': reasoning} if type(reasoning) is int and reasoning >= 0 else {}
    return SimpleNamespace(content=choice['message'].get('content'), usage_metadata=normalized,
                           response_metadata=metadata, id=body.get('id'),
                           finish_reason=finish if finish in {'stop', 'length', 'tool_calls', 'content_filter'} else None)
