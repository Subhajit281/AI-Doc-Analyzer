import chromadb


class ChromaVectorStore:

    def __init__(
        self,
        collection_name: str = "documents"
    ):
        self.client = chromadb.PersistentClient(
            path="./chroma_db"
        )

        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={
                "hnsw:space": "cosine"
            }
        )

    def add(
        self,
        ids: list[str],
        documents: list[str],
        embeddings,
        metadatas: list[dict]
    ):
        self.collection.add(
            ids=ids,
            documents=documents,
            embeddings=embeddings.tolist(),
            metadatas=metadatas
        )

    def search(
        self,
        query_embedding,
        top_k: int = 5,
        where: dict | None = None
    ):
        return self.collection.query(
            query_embeddings=[query_embedding.tolist()],
            n_results=top_k,
            where=where
        )