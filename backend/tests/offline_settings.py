"""Public dummy settings for generic tests; never reads a private allowance."""
import os
from unittest.mock import patch


def offline_environment():
    return patch.dict(os.environ, {
        'LLM_BACKEND':'azure_openai', 'LIVE_LLM_ENABLED':'false', 'FREE_ONLY':'true',
        'AZURE_OPENAI_API_KEY':'SYNTHETIC-ONLY', 'AZURE_OPENAI_ENDPOINT':'',
        'AZURE_OPENAI_DEPLOYMENT':'synthetic-deployment', 'AZURE_OPENAI_ALLOWANCE_FILE':'',
        'LLM_REQUEST_TIMEOUT_SECONDS':'30', 'HF_HUB_OFFLINE':'1',
        'TRANSFORMERS_OFFLINE':'1', 'ANONYMIZED_TELEMETRY':'false',
    })
