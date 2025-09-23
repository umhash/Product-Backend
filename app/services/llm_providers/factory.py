import os
from typing import Tuple

from .base import ChatLLM, Embeddings


def get_llm_backend() -> str:
    backend = os.getenv("LLM_BACKEND", "openai").strip().lower()
    return backend if backend in {"openai", "local"} else "openai"


def create_chat_and_embeddings() -> Tuple[ChatLLM, Embeddings]:
    """Factory to create chat and embeddings providers based on env switch."""
    backend = get_llm_backend()
    if backend == "local":
        from .local_chat import LocalChatProvider
        from .local_bge_embeddings import LocalBGEEmbeddingsProvider

        chat = LocalChatProvider()
        emb = LocalBGEEmbeddingsProvider()
        return chat, emb
    else:
        from .openai_chat import OpenAIChatProvider
        from .openai_embeddings import OpenAIEmbeddingsProvider

        chat = OpenAIChatProvider()
        emb = OpenAIEmbeddingsProvider()
        return chat, emb


