"""Load backend configuration from one fixed location, never the caller's cwd."""
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[3]
ENV_FILE = PROJECT_ROOT / '.env'


def load_environment(path: Path = ENV_FILE) -> None:
    # No interpolation: values must not expand unrelated process credentials.
    # Process variables, including deliberately empty values, always win.
    load_dotenv(dotenv_path=path, override=False, interpolate=False)


def resolve_path(value: str) -> Path:
    path = Path(value).expanduser()
    return path if path.is_absolute() else PROJECT_ROOT / path
