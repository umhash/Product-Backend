import os
from typing import List, Dict, Optional
import shutil
from huggingface_hub import hf_hub_download

from .base import ChatLLM


PREFERRED_MODELS = [
    # Prefer smaller models first for latency on local machines
    ("Qwen/Qwen2.5-3B-Instruct-GGUF", "qwen2.5-3b-instruct-q4_k_m.gguf", "qwen"),
    ("Qwen/Qwen2.5-7B-Instruct-GGUF", "qwen2.5-7b-instruct-q4_k_m.gguf", "qwen"),
    ("QuantFactory/Meta-Llama-3.1-8B-Instruct-GGUF", "Meta-Llama-3.1-8B-Instruct.Q4_K_M.gguf", "llama-3"),
]


class LocalChatProvider(ChatLLM):
    def __init__(self):
        # Ensure model file exists in repo-local folder, download if missing
        # project root: product-be (three levels up from this file)
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
        models_dir = os.path.join(base_dir, "models", "llm")
        os.makedirs(models_dir, exist_ok=True)

        self.model_path: Optional[str] = None
        self.chat_format: Optional[str] = None

        for repo_id, filename, chat_format in PREFERRED_MODELS:
            local_path = os.path.join(models_dir, filename)
            try:
                if not os.path.exists(local_path):
                    downloaded = hf_hub_download(repo_id=repo_id, filename=filename)
                    # Copy downloaded file from HF cache into repo-local models directory
                    os.makedirs(models_dir, exist_ok=True)
                    shutil.copy2(downloaded, local_path)
                if os.path.exists(local_path):
                    self.model_path = local_path
                    self.chat_format = chat_format
                    break
            except Exception:
                continue

        if not self.model_path:
            raise RuntimeError("No local chat model available. Failed to download Llama and Qwen GGUF.")

        # Lazy import to avoid dependency load when not using local
        from llama_cpp import Llama

        # Configure threads and context size; enable Metal if available (default in wheels)
        n_ctx = int(os.getenv("LOCAL_LLM_CTX", "8192"))
        n_threads = int(os.getenv("LOCAL_LLM_THREADS", str(os.cpu_count() or 4)))

        self.llm = Llama(
            model_path=self.model_path,
            n_ctx=n_ctx,
            n_threads=n_threads,
            chat_format=self.chat_format,
            verbose=False,
        )

    def generate(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int = 1024,
        temperature: float = 0.7,
        top_p: float = 0.9,
    ) -> str:
        # llama-cpp supports OpenAI-style messages via chat_format
        # Cap tokens for latency when running locally
        max_new_tokens = min(max_tokens, int(os.getenv("LOCAL_LLM_MAX_TOKENS", "384")))
        response = self.llm.create_chat_completion(
            messages=messages,
            temperature=temperature,
            top_p=top_p,
            max_tokens=max_new_tokens,
        )
        return response["choices"][0]["message"]["content"]


