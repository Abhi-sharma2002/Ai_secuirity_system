"""Load backend configuration from one fixed location, never the caller's cwd."""
from pathlib import Path
import os

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[3]
ENV_FILE = PROJECT_ROOT / '.env'
_azure_credential_source = 'unknown'
_openrouter_credential_source = 'unknown'


def load_environment(path: Path = ENV_FILE) -> None:
    global _azure_credential_source, _openrouter_credential_source
    azure_inherited = 'AZURE_OPENAI_API_KEY' in os.environ
    openrouter_inherited = 'OPENROUTER_API_KEY' in os.environ
    # No interpolation: values must not expand unrelated process credentials.
    # Process variables, including deliberately empty values, always win.
    load_dotenv(dotenv_path=path, override=False, interpolate=False)
    _azure_credential_source = ('process environment: AZURE_OPENAI_API_KEY' if azure_inherited else
                               'repository-root .env: AZURE_OPENAI_API_KEY' if path == ENV_FILE else
                               'alternate dotenv: AZURE_OPENAI_API_KEY')
    _openrouter_credential_source = ('process environment: OPENROUTER_API_KEY' if openrouter_inherited else
                                     'repository-root .env: OPENROUTER_API_KEY' if path == ENV_FILE else
                                     'alternate dotenv: OPENROUTER_API_KEY')


def credential_provenance(effective: str, provider: str = 'azure_openai') -> dict:
    """Called in the execution process; never returns credential material."""
    from dotenv import dotenv_values
    if provider == 'azure_openai':
        name, source = 'AZURE_OPENAI_API_KEY', _azure_credential_source
    elif provider == 'openrouter':
        name, source = 'OPENROUTER_API_KEY', _openrouter_credential_source
    else:
        return {'credential_source': 'historical provider: inactive', 'credential_matches_root_env': False}
    root = dotenv_values(ENV_FILE, interpolate=False).get(name)
    matches = isinstance(root, str) and effective == root.strip()
    if source == 'repository-root .env: '+name and not matches:
        source = 'process environment override: '+name
    return {'credential_source': source, 'credential_matches_root_env': matches}


def resolve_path(value: str) -> Path:
    path = Path(value).expanduser()
    return path if path.is_absolute() else PROJECT_ROOT / path
