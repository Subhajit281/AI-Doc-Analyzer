import os
import threading
import numpy as np
from typing import List

from dotenv import load_dotenv
load_dotenv()

from app.core.cache import query_embedding_cache


class DocumentEmbedder:
    """
    Zero-RAM embedding provider using Google Gemini API (default) with
    lazy-loaded local SentenceTransformers fallback.
    
    Using Gemini embeddings saves ~450 MB of RAM, allowing the entire application
    to run smoothly within a 512 MB free-tier platform.
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls, model_name: str | None = None):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    instance._initialize(model_name)
                    cls._instance = instance
        return cls._instance

    def _initialize(self, model_name: str | None = None):
        provider = os.getenv("EMBEDDING_PROVIDER", "").strip().lower()
        api_key = os.getenv("GEMINI_API_KEY")

        if provider == "local" or (not api_key and provider != "gemini"):
            print("[EMBEDDER] Initializing local SentenceTransformer (high RAM)...")
            os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
            os.environ.setdefault("OMP_NUM_THREADS", "1")
            import torch
            torch.set_num_threads(1)
            from sentence_transformers import SentenceTransformer

            self.provider = "local"
            local_model = model_name or "all-MiniLM-L6-v2"
            self.model = SentenceTransformer(local_model, device="cpu")
            self.client = None
        else:
            print("[EMBEDDER] Initializing GeminiEmbedder (0 MB RAM, model='models/gemini-embedding-001')...")
            from google import genai
            self.provider = "gemini"
            self.model_name = "models/gemini-embedding-001"
            self.client = genai.Client(api_key=api_key)
            self.model = None

    def embed(self, text: str) -> np.ndarray:
        """
        Embed a single text string with caching.
        """
        cache_key = f"{self.provider}:{text.strip()}"
        cached = query_embedding_cache.get(cache_key)
        if cached is not None:
            return cached

        if self.provider == "gemini":
            res = self.client.models.embed_content(
                model=self.model_name,
                contents=text.strip(),
            )
            embedding = np.array(res.embeddings[0].values, dtype=np.float32)
        else:
            embedding = self.model.encode(text, normalize_embeddings=True)
            if not isinstance(embedding, np.ndarray):
                embedding = np.array(embedding, dtype=np.float32)

        query_embedding_cache.set(cache_key, embedding)
        return embedding

    def embed_many(self, texts: List[str], batch_size: int = 32) -> np.ndarray:
        """
        Embed multiple texts in batches.
        """
        if not texts:
            return np.array([], dtype=np.float32)

        if self.provider == "gemini":
            all_embeddings = []
            # Batch calls to avoid request size limits
            for i in range(0, len(texts), batch_size):
                batch = texts[i : i + batch_size]
                res = self.client.models.embed_content(
                    model=self.model_name,
                    contents=batch,
                )
                for emb in res.embeddings:
                    all_embeddings.append(emb.values)
            return np.array(all_embeddings, dtype=np.float32)

        else:
            return self.model.encode(texts, normalize_embeddings=True, batch_size=batch_size)