import os
from typing import List
import numpy as np
from huggingface_hub import snapshot_download

from .base import Embeddings


class LocalBGEEmbeddingsProvider(Embeddings):
    def __init__(self):
        # Repo-local model path under product-be/models
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
        model_dir = os.path.join(base_dir, "models", "embeddings", "bge-m3")
        os.makedirs(model_dir, exist_ok=True)

        # Lazy import to avoid cost when not used
        from sentence_transformers import SentenceTransformer

        # Ensure model exists under repo models dir; download snapshot if missing
        preferred_id = "BAAI/bge-m3"
        # Heuristic: presence of config files indicates downloaded
        expected_file = os.path.join(model_dir, "config.json")
        if not os.path.exists(expected_file):
            try:
                snapshot_download(repo_id=preferred_id, local_dir=model_dir, local_dir_use_symlinks=False)
            except Exception:
                # If download fails but directory already has something, proceed; else re-raise
                if not os.path.exists(model_dir) or not os.listdir(model_dir):
                    raise

        # Load from the repo-local directory
        self.model = SentenceTransformer(model_dir)

        self._dim = 1024

    @property
    def embedding_dim(self) -> int:
        return self._dim

    def embed(self, texts: List[str]) -> List[List[float]]:
        vectors = self.model.encode(texts, normalize_embeddings=True, convert_to_numpy=True)
        if isinstance(vectors, list):
            return vectors
        # Ensure list of lists
        return [vec.astype(np.float32).tolist() for vec in np.atleast_2d(vectors)]


