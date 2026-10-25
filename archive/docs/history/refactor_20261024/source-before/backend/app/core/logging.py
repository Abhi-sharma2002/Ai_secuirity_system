"""Configure operational logging without logging questions or document text."""
import logging
from app.core.config import settings


def configure_logging() -> None:
    logging.basicConfig(level=settings.log_level,
                        format='%(asctime)s | %(levelname)s | %(name)s | %(message)s')

    # SDK debug logging can include request bodies; never inherit application DEBUG.
    for name in ('groq', 'langchain_groq', 'google.genai', 'langchain_google_genai', 'httpx', 'httpx2', 'httpcore', 'langchain', 'langsmith'):
        logging.getLogger(name).setLevel(logging.WARNING)
