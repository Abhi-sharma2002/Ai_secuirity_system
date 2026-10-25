"""Compatibility import for the shared Phase 4 client; no RAG or defense policy."""
from legacy_llm.client import LLMClient, LLMRequestError, create_client
from legacy_llm.models import LLMConfig, LLMRequest, Message

__all__ = ['LLMClient', 'LLMRequestError', 'create_client', 'LLMConfig', 'LLMRequest', 'Message']
