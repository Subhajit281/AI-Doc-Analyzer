from sentence_transformers import SentenceTransformer


class DocumentEmbedder:

    def __init__(
        self,
        model_name: str = "all-MiniLM-L6-v2"
    ):
        self.model = SentenceTransformer(model_name)

    def embed(self, text: str):
        return self.model.encode(
            text,
            normalize_embeddings=True
        )

    def embed_many(self, texts: list[str]):
        return self.model.encode(
            texts,
            normalize_embeddings=True
        )