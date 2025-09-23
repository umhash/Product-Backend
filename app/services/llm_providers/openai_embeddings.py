import os
from typing import List
from openai import OpenAI

from .base import Embeddings


class OpenAIEmbeddingsProvider(Embeddings):
    def __init__(self):
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key or api_key == "your-openai-api-key-here":
            raise ValueError("OPENAI_API_KEY environment variable is required")
        self.client = OpenAI(api_key=api_key)
        # text-embedding-3-large is 3072-dim
        self.model = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-large")
        self._dim = 3072

    @property
    def embedding_dim(self) -> int:
        return self._dim

    def embed(self, texts: List[str]) -> List[List[float]]:
        response = self.client.embeddings.create(model=self.model, input=texts)
        return [d.embedding for d in response.data]


