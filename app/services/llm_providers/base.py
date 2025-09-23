import abc
from typing import List, Dict, Any


class ChatLLM(abc.ABC):
    """Abstract interface for chat LLMs."""

    @abc.abstractmethod
    def generate(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int = 1024,
        temperature: float = 0.7,
        top_p: float = 0.9,
    ) -> str:
        """Generate a chat completion given OpenAI-style messages."""
        raise NotImplementedError


class Embeddings(abc.ABC):
    """Abstract interface for text embedding models."""

    @property
    @abc.abstractmethod
    def embedding_dim(self) -> int:
        raise NotImplementedError

    @abc.abstractmethod
    def embed(self, texts: List[str]) -> List[List[float]]:
        """Return embeddings for a list of texts."""
        raise NotImplementedError


