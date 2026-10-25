"""Human-readable explanations from allowlisted operational metadata only."""
def describe_error(result):
    traces=result.get('calls') or []
    last=traces[-1] if traces else {}
    if last.get('exception_type') == 'ConnectError':
        return 'Could not connect to the model provider. No HTTP response was captured; the cause is not established. The allowance stopped and no automatic retry was made.'
    if last.get('error') == 'timeout_usage_unknown':
        return 'The model service did not respond before the request timeout. Usage is unknown; no automatic retry was made.'
    validation=last.get('response_validation_error')
    if last.get('finish_reason') == 'length' and validation == 'invalid_json':
        return 'The model hit the output-token limit before returning valid JSON. No usable answer was produced. No automatic retry was made.'
    usage=last.get('usage') or {}
    cap=(last.get('settings') or {}).get('max_output_tokens')
    historical_missing=(last.get('exception_type')=='ValueError' and type(cap) is int
                        and usage.get('output_tokens')==cap)
    if validation in {'non_text_content','empty_content','empty_response'} or historical_missing:
        return 'The model returned no usable final answer within the output limit. No automatic retry was made.'
    if validation=='invalid_json':
        return 'The model response did not match the required JSON format. No automatic retry was made.'
    status=last.get('http_status')
    provider=(last.get('settings') or {}).get('provider')
    provider_name='OpenRouter' if provider=='openrouter' else 'Azure' if provider=='azure_openai' else 'The model provider'
    if last.get('provider_error_code') in {'content_filter','ResponsibleAIPolicyViolation','content_policy_violation'}:
        return f'{provider_name} rejected the request under its content policy. This is an operational rejection, not evidence that a defense resisted the attack. No retry was made.'
    if status == 400:
        return f'{provider_name} rejected the request (HTTP 400). Saved diagnostics may not establish the precise cause. This is not a defense success; no retry was made.'
    if status in {401,403}:
        return f'{provider_name} rejected authentication or access. Check the backend configuration privately; no retry was made.'
    if status == 429:
        return f'{provider_name} reported a quota or rate limit. The allowance is stopped; no automatic retry was made.'
    if status == 402:
        return f'{provider_name} reported insufficient credits or a payment requirement. The allowance is stopped; no retry was made.'
    if type(status) is int and status>=500:
        return f'The model service returned a server error (HTTP {status}). No automatic retry was made.'
    return 'The model request failed. See the saved diagnostics below; no fallback answer was generated.'
