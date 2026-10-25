"""Load backend configuration from one fixed location, never the caller's cwd."""
from pathlib import Path
import os

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[3]
ENV_FILE = PROJECT_ROOT / '.env'
_credential_source = 'unknown'
_nvidia_credential_source = 'unknown'
_azure_credential_source = 'unknown'


def load_environment(path: Path = ENV_FILE) -> None:
    global _credential_source, _nvidia_credential_source, _azure_credential_source
    inherited = 'GROQ_API_KEY' in os.environ
    nvidia_inherited = 'NVIDIA_API_KEY' in os.environ
    azure_inherited = 'AZURE_OPENAI_API_KEY' in os.environ
    # No interpolation: values must not expand unrelated process credentials.
    # Process variables, including deliberately empty values, always win.
    load_dotenv(dotenv_path=path, override=False, interpolate=False)
    _credential_source = ('process environment: GROQ_API_KEY' if inherited else
                          'repository-root .env: GROQ_API_KEY' if path == ENV_FILE else
                          'alternate dotenv: GROQ_API_KEY')
    _nvidia_credential_source = ('process environment: NVIDIA_API_KEY' if nvidia_inherited else
                                'repository-root .env: NVIDIA_API_KEY' if path == ENV_FILE else
                                'alternate dotenv: NVIDIA_API_KEY')
    _azure_credential_source = ('process environment: AZURE_OPENAI_API_KEY' if azure_inherited else
                               'repository-root .env: AZURE_OPENAI_API_KEY' if path == ENV_FILE else
                               'alternate dotenv: AZURE_OPENAI_API_KEY')


def credential_provenance(effective: str, provider: str = 'azure_openai') -> dict:
    """Called in the execution process; never returns credential material."""
    from dotenv import dotenv_values
    name = {'azure_openai': 'AZURE_OPENAI_API_KEY', 'nvidia_nim': 'NVIDIA_API_KEY'}.get(provider, 'GROQ_API_KEY')
    root = dotenv_values(ENV_FILE, interpolate=False).get(name)
    matches = isinstance(root, str) and effective == root.strip()
    source = {'azure_openai': _azure_credential_source, 'nvidia_nim': _nvidia_credential_source}.get(provider, _credential_source)
    if source == 'repository-root .env: '+name and not matches:
        source = 'process environment override: '+name
    return {'credential_source': source, 'credential_matches_root_env': matches}


def resolve_path(value: str) -> Path:
    path = Path(value).expanduser()
    return path if path.is_absolute() else PROJECT_ROOT / path
