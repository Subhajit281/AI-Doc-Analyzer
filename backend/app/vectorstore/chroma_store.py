import threading
import chromadb


class ChromaVectorStore:
    """
    Process-wide singleton, same reasoning as DocumentEmbedder/DoclingParser.

    embedding_function=None is critical: without it, Chroma silently loads
    its own onnxruntime-based default embedder even though we always pass
    precomputed embeddings to .add()/.query() ourselves. That was a second,
    unused embedding model sitting in memory.
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls, collection_name: str = "documents"):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    instance.client = chromadb.PersistentClient(path="./chroma_db")
                    instance.collection = instance.client.get_or_create_collection(
                        name=collection_name,
                        metadata={"hnsw:space": "cosine"},
                        embedding_function=None,
                    )
                    cls._instance = instance
        return cls._instance

    def add(self, ids: list[str], documents: list[str], embeddings, metadatas: list[dict]):
        self.collection.add(
            ids=ids,
            documents=documents,
            embeddings=embeddings.tolist(),
            metadatas=metadatas,
        )

    def search(self, query_embedding, top_k: int = 5, where: dict | None = None):
        return self.collection.query(
            query_embeddings=[query_embedding.tolist()],
            n_results=top_k,
            where=where,
        )