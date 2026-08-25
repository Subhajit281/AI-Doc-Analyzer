import os
import threading

os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
os.environ.setdefault("OMP_NUM_THREADS", "1")

import torch
from sentence_transformers import SentenceTransformer

torch.set_num_threads(1)


class DocumentEmbedder:
    """
    Process-wide singleton. document_service and query_service each
    call DocumentEmbedder() independently — without __new__ caching,
    that's two separate SentenceTransformer instances (two copies of
    the model weights + torch runtime) alive at once.
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls, model_name: str = "all-MiniLM-L6-v2"):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    instance.model = SentenceTransformer(model_name, device="cpu")
                    cls._instance = instance
        return cls._instance

    def embed(self, text: str):
        return self.model.encode(text, normalize_embeddings=True)

    def embed_many(self, texts: list[str], batch_size: int = 8):
        return self.model.encode(texts, normalize_embeddings=True, batch_size=batch_size)