"""Validated, process-wide settings. Paths default to the backend directory."""
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from app.core.environment import resolve_path

ROOT = Path(__file__).resolve().parents[2]


def path_setting(name: str, default: Path) -> Path:
    value = os.getenv(name, '').strip()
    return resolve_path(value) if value else default


def boolean(name: str, default: bool) -> bool:
    value = os.getenv(name, str(default)).strip().lower()
    if value not in {'true', 'false'}:
        raise ValueError(f'{name} must be true or false')
    return value == 'true'


@dataclass(frozen=True)
class LiveSettings:
    """Read at each live gate so disabling/expiry checks cannot use stale settings."""
    free_only: bool
    enabled: bool
    api_key: str = field(repr=False)
    model: str = field(repr=False)
    allowance_file: Path | None = None
    request_timeout_seconds: float = 30.0
    provider: str = 'azure_openai'
    base_url: str = ''
    auth_mode: str = 'api-key'
    reasoning_effort: str | None = None

    @classmethod
    def from_env(cls):
        free_only = boolean('FREE_ONLY', True)
        enabled = boolean('LIVE_LLM_ENABLED', False)
        provider = os.getenv('LLM_BACKEND', 'azure_openai').strip().lower()
        if provider != 'azure_openai':
            raise ValueError('LLM_BACKEND must be azure_openai; historical providers are disabled')
        key = os.getenv('AZURE_OPENAI_API_KEY', '').strip()
        model = os.getenv('AZURE_OPENAI_DEPLOYMENT', '').strip()
        base_url = azure_base_url(os.getenv('AZURE_OPENAI_ENDPOINT', '').strip())
        if enabled:
            missing = [name for name, value in (
                ('AZURE_OPENAI_API_KEY', key), ('AZURE_OPENAI_ENDPOINT', base_url),
                ('AZURE_OPENAI_DEPLOYMENT', model)) if not value]
            if missing:
                raise ValueError('Live Azure configuration missing: ' + ', '.join(missing))
        try:
            timeout = float(os.getenv('LLM_REQUEST_TIMEOUT_SECONDS', '30'))
            import math
            if not math.isfinite(timeout) or timeout <= 0:
                raise ValueError()
        except ValueError:
            raise ValueError('LLM_REQUEST_TIMEOUT_SECONDS must be finite and positive') from None
        allowance = os.getenv('AZURE_OPENAI_ALLOWANCE_FILE', '.private/azure_allowance.json').strip()
        return cls(free_only, enabled, key, model,
                   resolve_path(allowance) if allowance else None, timeout, provider, base_url, 'api-key', None)


def azure_base_url(endpoint: str) -> str:
    """Accept Azure resource roots or the v1 base; never redirect keys elsewhere."""
    if not endpoint:
        return ''
    from urllib.parse import urlsplit
    try:
        url = urlsplit(endpoint)
        valid = (url.scheme == 'https' and url.hostname and not url.username and not url.password
                 and not url.query and not url.fragment and url.port in (None, 443)
                 and url.path.rstrip('/') in ('', '/openai/v1', '/openai/v1/responses', '/openai/v1/chat/completions')
                 and any(url.hostname.endswith(suffix) for suffix in (
                     '.openai.azure.com', '.services.ai.azure.com', '.cognitiveservices.azure.com',
                     '.openai.azure.us', '.openai.azure.cn')))
    except ValueError:
        valid = False
    if not valid:
        raise ValueError('AZURE_OPENAI_ENDPOINT must be an HTTPS Azure resource root or /openai/v1 base, without credentials, query or deployment path')
    return f'https://{url.hostname}/openai/v1'


def integer(name: str, default: int, minimum: int = 1) -> int:
    try:
        value = int(os.getenv(name, str(default)))
    except ValueError as exc:
        raise ValueError(f'{name} must be an integer') from exc
    if value < minimum:
        raise ValueError(f'{name} must be >= {minimum}')
    return value


@dataclass(frozen=True)
class Settings:
    document_directory: Path = path_setting('DOCUMENT_DIRECTORY', ROOT / 'data/documents')
    upload_directory: Path = path_setting('UPLOAD_DIRECTORY', ROOT / 'data/uploads')
    db_path: Path = path_setting('CHROMA_DB_PATH', ROOT / 'data/chroma_db')
    app_data_directory: Path = path_setting('APP_DATA_DIRECTORY', ROOT / 'data/runtime')
    embedding_model: str = os.getenv('EMBEDDING_MODEL', 'sentence-transformers/all-MiniLM-L6-v2')
    embedding_revision: str = os.getenv('EMBEDDING_REVISION', '1110a243fdf4706b3f48f1d95db1a4f5529b4d41')
    embedding_dimension: int = integer('EMBEDDING_DIMENSION', 384)
    chunk_size: int = integer('CHUNK_SIZE', 1000)
    chunk_overlap: int = integer('CHUNK_OVERLAP', 150, 0)
    batch_size: int = integer('EMBEDDING_BATCH_SIZE', 16)
    top_k: int = integer('RETRIEVAL_TOP_K', 5)
    evidence_max_characters: int = integer('EVIDENCE_MAX_CHARACTERS', 100_000)
    evidence_max_bytes: int = integer('EVIDENCE_MAX_BYTES', 400_000)
    max_file_size: int = integer('MAX_DOCUMENT_BYTES', 5 * 1024 * 1024)
    ignored_document_entries: tuple[str, ...] = tuple(
        name.strip() for name in os.getenv("IGNORED_DOCUMENT_ENTRIES", ".gitkeep").split(",") if name.strip()
    )
    log_level: str = os.getenv('LOG_LEVEL', 'INFO').upper()

    def __post_init__(self) -> None:
        if self.chunk_overlap >= self.chunk_size:
            raise ValueError('CHUNK_OVERLAP must be smaller than CHUNK_SIZE')
        if self.top_k > 20:
            raise ValueError('RETRIEVAL_TOP_K must be <= 20')
        if not self.embedding_model.strip() or not self.embedding_revision.strip():
            raise ValueError('Embedding model and revision cannot be empty')
        if not re.fullmatch(r'[0-9a-f]{40}', self.embedding_revision):
            raise ValueError('EMBEDDING_REVISION must be an immutable 40-character commit SHA')
        if self.log_level not in {'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'}:
            raise ValueError('Invalid LOG_LEVEL')


settings = Settings()
