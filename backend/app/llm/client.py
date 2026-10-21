"""Groq-only live provider boundary. Persistent conservative reservations precede every call."""
import hashlib
import json
import time
from datetime import datetime, timezone
from uuid import uuid4
from pydantic import BaseModel, ConfigDict, Field
from app.core import registry as reg
from app.core.config import LiveSettings


class LiveBlocked(RuntimeError):
    pass


class ModelFailure(RuntimeError):
    def __init__(self, category, record):
        self.category, self.record = category, record
        super().__init__(category)


class Approval(BaseModel):
    model_config = ConfigDict(extra='forbid')
    provider: str = Field(pattern='^groq$')
    allowance_id: str = Field(min_length=1, max_length=100)
    confirmed_free_promotional: bool
    approved_model: str = Field(min_length=1)
    expires_at: datetime
    max_calls: int = Field(gt=0, le=1000)
    max_reserved_tokens: int = Field(gt=0, le=10_000_000)
    chat_completions_supported: bool
    structured_outputs_supported: bool
    max_output_tokens_supported: bool
    confirmation_note: str = Field(min_length=10)


def approval():
    try:
        config = LiveSettings.from_env()
    except ValueError as exc:
        raise LiveBlocked(str(exc)) from None
    if not config.free_only:
        raise LiveBlocked('This application requires FREE_ONLY=true')
    if not config.enabled:
        raise LiveBlocked('Live Groq is disabled. Complete local setup and confirm actual free allowance before enabling it.')
    try:
        path = config.allowance_file
        if path.stat().st_size > 10_000:
            raise ValueError()
        approved = Approval.model_validate_json(path.read_text())
    except Exception:
        raise LiveBlocked('A valid operator-created FREE_ALLOWANCE_FILE is required; see docs/FREE_ALLOWANCE.example.json') from None
    if (not approved.confirmed_free_promotional or approved.approved_model != config.model
        or approved.expires_at.tzinfo is None or approved.expires_at <= datetime.now(timezone.utc)
        or not all((approved.chat_completions_supported, approved.structured_outputs_supported,
                    approved.max_output_tokens_supported))):
        raise LiveBlocked('Free allowance expired, model mismatched, or model API capabilities unconfirmed')
    import importlib.util
    if importlib.util.find_spec('langchain_groq') is None:
        raise LiveBlocked('Groq dependency is missing. Install backend/requirements.txt before enabling live calls.')
    return approved


def readiness():
    try:
        a = approval()
        return {'enabled': True, 'model': a.approved_model, 'allowance_id': a.allowance_id}
    except LiveBlocked as exc:
        return {'enabled': False, 'reason': str(exc)}


def reserve(calls, tokens, metadata=None):
    if type(calls) is not int or type(tokens) is not int or calls <= 0 or tokens < calls:
        raise LiveBlocked('Reservations require positive integer calls and at least one token per call')
    a = approval()
    # Bind limits/expiry/model to the same ledger ID: editing a file cannot reset counters.
    identity = hashlib.sha256(a.model_dump_json().encode()).hexdigest()
    with reg.LOCK, reg.connect() as db:
        db.execute('INSERT OR IGNORE INTO allowance VALUES(?,?,?,0)', (identity, 0, 0))
        row = db.execute('SELECT * FROM allowance WHERE id=?', (identity,)).fetchone()
        # The file fingerprint is a receipt, but allowance_id binds cumulative usage across edits.
        used = db.execute("SELECT data FROM calls WHERE allowance_id=?", (a.allowance_id,)).fetchall()
        if any(json.loads(r['data']).get('error') in {'insufficient_quota', 'quota_or_rate_limit'} for r in used):
            raise LiveBlocked('Provider quota stopped this allowance; no more requests permitted')
        prior_calls = len(used)
        prior_tokens = sum(json.loads(r['data']).get('reservation', 0) for r in used)
        if row['stopped'] or prior_calls + calls > a.max_calls or prior_tokens + tokens > a.max_reserved_tokens:
            raise LiveBlocked('Local call/token allowance exhausted or stopped; no request sent')
        db.execute('UPDATE allowance SET calls=calls+?, tokens=tokens+? WHERE id=?', (calls, tokens, identity))
        ids = [str(uuid4()) for _ in range(calls)]
        each, remainder = divmod(tokens, calls)
        for n, call_id in enumerate(ids):
            db.execute('INSERT INTO calls VALUES(?,?,?,?,?)', (call_id, a.allowance_id, 'reserved', 'reserved',
                       json.dumps({'reservation': each + (1 if n < remainder else 0), 'approval_fingerprint': identity, 'context': metadata or {}, 'reserved_at': datetime.now(timezone.utc).isoformat()})))
    return ids


def call(messages, schema, stage, reservation):
    a = approval()  # Recheck expiry and gate immediately before I/O.
    with reg.LOCK, reg.connect() as db:
        row = db.execute('SELECT * FROM calls WHERE id=? AND status=?', (reservation, 'reserved')).fetchone()
        if row is None or row['allowance_id'] != a.allowance_id:
            raise LiveBlocked('Missing or already consumed call reservation')
        data = json.loads(row['data'])
        if data.get('approval_fingerprint') != hashlib.sha256(a.model_dump_json().encode()).hexdigest():
            raise LiveBlocked('Reservation approval changed; create a new reservation under the current approval')
        upper_bound = sum(len(str(m).encode()) for m in messages) + len(json.dumps(schema).encode()) + 1800
        if upper_bound > data['reservation']:
            raise LiveBlocked('Request exceeds conservative reserved token bound')
        data['started_at'] = datetime.now(timezone.utc).isoformat()
        db.execute("UPDATE calls SET status='started', stage=?, data=? WHERE id=?", (stage, json.dumps(data), reservation))
    started = time.perf_counter()
    record = {'context': data.get('context', {}), 'call_id': reservation, 'stage': stage, 'model': a.approved_model, 'usage': None,
              'provider_request_id': None, 'attempts': 1, 'settings': {'provider': 'groq', 'api': 'chat_completions',
              'max_output_tokens': 700, 'max_retries': 0, 'temperature': 1.0}}
    error = None
    output = None
    try:
        from langchain_groq import ChatGroq
        from langchain_core.messages import SystemMessage, HumanMessage
        config = LiveSettings.from_env()
        # Normalize trusted application rules into one system message.
        # Combine only application-controlled privileged messages; never source text.
        privileged, untrusted = [], []
        for message in messages:
            if message['role'] in {'system', 'developer'}:
                privileged.append(message['content'])
            elif message['role'] == 'user':
                untrusted.append(HumanMessage(content=message['content']))
            else:
                raise ValueError('unsupported_message_role')
        prompt = ([SystemMessage(content='\n\n'.join(privileged))] if privileged else []) + untrusted
        model = ChatGroq(model=a.approved_model, api_key=config.api_key,
            base_url='https://api.groq.com',
            max_retries=0, timeout=config.request_timeout_seconds,
            max_tokens=700, temperature=1.0)
        # Bind the wire format explicitly: the SDK's convenience helper can silently
        # drop strict=True for model IDs absent from its internal allowlist.
        reply = model.bind(response_format={'type': 'json_schema', 'json_schema': {
            'name': schema.get('title', 'security_response'), 'strict': True, 'schema': schema,
        }}).invoke(prompt, config={'callbacks': []})
        record['usage'] = reply.usage_metadata
        record['provider_request_id'] = reply.response_metadata.get('request_id')
        record['response_id'] = reply.id
        if not isinstance(reply.content, str):
            raise ValueError('invalid_response')
        output = json.dumps(json.loads(reply.content), ensure_ascii=True)
        # The shared assistant independently validates Answer/Screening and source IDs.
    except Exception as exc:
        # SDK error text can contain keys/requests; persist categories only.
        # Read status codes without persisting provider error text.
        cause, code, seen = exc, None, set()
        while cause is not None and id(cause) not in seen:
            seen.add(id(cause))
            candidate = getattr(cause, 'status_code', None) or getattr(cause, 'code', None)
            if isinstance(candidate, int):
                code = candidate
                break
            cause = cause.__cause__ or cause.__context__
        record['exception_type'] = type(exc).__name__
        record['http_status'] = code
        if code == 429:
            error = 'quota_or_rate_limit'
        elif code in {401, 403}:
            error = 'authentication_or_permission'
        elif code == 404:
            error = 'unavailable_model'
        elif code == 400:
            error = 'invalid_request_or_unsupported_parameters'
        elif isinstance(exc, TimeoutError):
            error = 'timeout_usage_unknown'
        else:
            import httpx
            error = 'timeout_usage_unknown' if isinstance(exc, httpx.TimeoutException) else 'provider_or_schema_error'
    record['latency_ms'] = (time.perf_counter() - started) * 1000
    record['error'] = error
    with reg.LOCK, reg.connect() as db:
        db.execute('UPDATE calls SET status=?, data=? WHERE id=?',
            ('failed' if error else 'completed', json.dumps({**data, **record}), reservation))
        if error in {'insufficient_quota', 'quota_or_rate_limit'}:
            db.execute('UPDATE allowance SET stopped=1 WHERE id=?', (data['approval_fingerprint'],))
            # A quota error stops this allowance even if the approval file is later edited.
            db.execute("UPDATE calls SET status='quota_stopped' WHERE allowance_id=? AND status='reserved'", (a.allowance_id,))
    if error:
        raise ModelFailure(error, record)
    return output, record
