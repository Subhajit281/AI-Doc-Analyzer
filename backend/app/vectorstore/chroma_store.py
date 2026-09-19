import hashlib
import os
import threading
import chromadb
from app.core.cache import search_result_cache


class ChromaVectorStore:
    """
    Process-wide singleton with provider-aware collection namespaces.

    embedding_function=None is critical: without it, Chroma silently loads
    its own onnxruntime-based default embedder even though we always pass
    precomputed embeddings to .add()/.query() ourselves. That was a second,
    unused embedding model sitting in memory.
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls, collection_name: str | None = None):
        provider = os.getenv("EMBEDDING_PROVIDER", "").strip().lower()
        if not provider:
            provider = "gemini" if os.getenv("GEMINI_API_KEY") else "local"

        base_name = collection_name or "documents"
        resolved_name = f"{base_name}_{provider}" if provider == "gemini" else base_name

        if cls._instance is None or getattr(cls._instance, "_collection_name", None) != resolved_name:
            with cls._lock:
                if cls._instance is None or getattr(cls._instance, "_collection_name", None) != resolved_name:
                    instance = super().__new__(cls)
                    instance.client = chromadb.PersistentClient(path="./chroma_db")
                    instance.collection = instance.client.get_or_create_collection(
                        name=resolved_name,
                        metadata={"hnsw:space": "cosine"},
                        embedding_function=None,
                    )
                    instance._collection_name = resolved_name
                    cls._instance = instance
        return cls._instance

    def add(self, ids: list[str], documents: list[str], embeddings, metadatas: list[dict]):
        emb_list = embeddings.tolist() if hasattr(embeddings, "tolist") else list(embeddings)
        self.collection.add(
            ids=ids,
            documents=documents,
            embeddings=emb_list,
            metadatas=metadatas,
        )

    def search(self, query_embedding, top_k: int = 5, where: dict | None = None):
        emb_list = query_embedding.tolist() if hasattr(query_embedding, "tolist") else list(query_embedding)

        # LRU cache key for search results
        where_key = str(sorted(where.items())) if where else ""
        cache_key = hashlib.md5(f"{emb_list[:4]}:{emb_list[-4:]}:{where_key}:{top_k}".encode()).hexdigest()

        cached = search_result_cache.get(cache_key)
        if cached is not None:
            return cached

        results = self.collection.query(
            query_embeddings=[emb_list],
            n_results=top_k,
            where=where,
        )
        search_result_cache.set(cache_key, results)
        return results