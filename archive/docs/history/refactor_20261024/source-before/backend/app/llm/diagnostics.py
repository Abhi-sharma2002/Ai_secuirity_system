"""Fail-closed, allowlisted metadata only. Never serialize SDK exceptions/requests."""
import re
from urllib.parse import quote, quote_plus
from app.core.environment import credential_provenance


def sanitize(value, credential, limit=512):
    if not isinstance(value, (str, int)) or isinstance(value, bool):
        return None
    text = str(value)
    if len(text) > 16384:
        return '[omitted: oversized diagnostic]'
    # Redact before truncation, including common encoded echoes.
    if credential:
        for secret in {credential, quote(credential, safe=''), quote_plus(credential)}:
            text = text.replace(secret, '[REDACTED]')
    text = re.sub(r'(?i)\b(?:bearer|authorization|cookie|set-cookie|api[_ -]?key|token|secret|password)\s*[:=]?\s*[^\s,;]+', '[REDACTED]', text)
    text = re.sub(r'(?i)\b(?:gsk_|sk-|sk_)[A-Za-z0-9_.*-]+', '[REDACTED]', text)
    text = re.sub(r'[A-Za-z0-9_+/=-]{16,}', '[REDACTED]', text)
    # Error prose is untrusted input. Retain a small authentication vocabulary,
    # suppressing arbitrary echoed identifiers, short key fragments and cookies.
    safe = set('invalid api key authentication authorization unauthorized permission denied access forbidden missing expired revoked credential credentials incorrect not valid provided the is was has been or and to for this request account project model error failed failure please check your an a'.split())
    text = re.sub(r'[A-Za-z0-9_./+*=-]+', lambda m: m[0] if m[0].lower() in safe or m[0]=='REDACTED' else '[REDACTED]', text)
    return ''.join(c if c.isprintable() else ' ' for c in text)[:limit]


def identifier(value, credential):
    if not isinstance(value, str) or len(value)>128:
        return None
    if credential and credential in value:
        return '[REDACTED]'
    if re.search(r'(?i)(?:gsk_|sk-|nvapi-|bearer|cookie|authorization)', value):
        return '[REDACTED]'
    return value if re.fullmatch(r'[A-Za-z0-9_-]{1,128}',value) else '[REDACTED]'


def provenance(config):
    return credential_provenance(config.api_key, config.provider)


def destination(request, expected_base_url=None):
    # Fixed endpoint allowlist: never persist arbitrary URL path/userinfo/query.
    u=request.url
    if expected_base_url:
        from urllib.parse import urlsplit
        expected=urlsplit(expected_base_url.rstrip('/')+'/chat/completions')
        if (u.scheme,u.host,u.port or (443 if u.scheme=='https' else 80),u.path)==(expected.scheme,expected.hostname,expected.port or (443 if expected.scheme=='https' else 80),expected.path):
            return {'scheme':u.scheme,'host':u.host,'path':u.path}
    return {'scheme':None,'host':None,'path':None,'unexpected_destination':True}


def error_details(exc, credential):
    result={'provider_error_type':None,'provider_error_code':None,'provider_error_message':None,
            'provider_request_id':None, 'provider_error_parameter':None,
            'provider_inner_error_code':None, 'provider_content_filter_categories':None,
            'diagnostic_detail_policy':'allowlisted_only; unknown metadata omitted; sanitized explanation may be insufficient'}
    seen=set()
    while exc is not None and id(exc) not in seen:
        seen.add(id(exc))
        body=getattr(exc,'body',None)
        if isinstance(body,dict):
            body=body.get('error',body)
            if isinstance(body,dict):
                # No stringification of whole bodies or arbitrary nested objects.
                for field in ('type','code'):
                    value=body.get(field)
                    # Unknown machine strings may themselves be echoed credentials.
                    allowed={'authentication_error','invalid_api_key','invalid_request_error',
                             'permission_error','permission_denied','unauthorized','invalid_authentication',
                             'rate_limit_error','rate_limit_exceeded','insufficient_quota',
                             'model_not_found','invalid_request','server_error',
                             'content_filter','ResponsibleAIPolicyViolation','content_policy_violation',
                             'unsupported_parameter','unsupported_value','invalid_parameter'}
                    if value is not None:
                        result['provider_error_'+field]=(value if isinstance(value,str) and value in allowed
                            and not (credential and credential in value) else '[REDACTED]')
                result['provider_error_message']=sanitize(body.get('message'),credential)
                parameter=body.get('param')
                parameters={'temperature','seed','max_completion_tokens','max_tokens','response_format',
                            'messages','model','top_p','reasoning_effort','stream'}
                if parameter is not None:
                    result['provider_error_parameter']=(parameter if isinstance(parameter,str)
                        and parameter in parameters and not (credential and credential in parameter) else '[REDACTED]')
                inner=body.get('innererror')
                if isinstance(inner,dict):
                    code=inner.get('code')
                    if code is not None:
                        result['provider_inner_error_code']=(code if isinstance(code,str) and code in allowed
                            and not (credential and credential in code) else '[REDACTED]')
                filters=(inner.get('content_filter_result') if isinstance(inner,dict) else None)
                if not isinstance(filters,dict):
                    filters=body.get('content_filter_result')
                if isinstance(filters,dict):
                    categories={'jailbreak','hate','sexual','violence','self_harm',
                                'protected_material_text','protected_material_code'}
                    result['provider_content_filter_categories']=sorted(name for name in categories
                        if not (credential and credential in name) and isinstance(filters.get(name),dict)
                        and filters[name].get('filtered') is True)

        response=getattr(exc,'response',None)
        if response is not None:
            result['provider_request_id']=identifier(response.headers.get('apim-request-id') or response.headers.get('x-request-id'),credential)
        if result['provider_request_id'] is None:
            result['provider_request_id']=identifier(getattr(exc,'request_id',None),credential)
        exc=exc.__cause__ or exc.__context__
    return result
