"""LLM integration layer used by the travel agent runtime."""

# LLM Module
from .langchain_adapter import (
    LangChainLLMAdapter,
    create_langchain_llm,
    create_from_yaml_config
)

__all__ = [
    'LangChainLLMAdapter',
    'create_langchain_llm',
    'create_from_yaml_config'
]
