from sentence_transformers import SentenceTransformer
from tenacity import retry, stop_after_attempt, wait_fixed

from core.config import settings
from core.logger import logger
from models.model_registry import model_registry


class HFEmbeddingClient:
    def __init__(self):
        self.model_name = settings.HF_EMBEDDING_MODEL
        self.model = None

    def load_model(self):
        if self.model is None:
            logger.info(f"Loading embedding model: {self.model_name}")

            self.model = SentenceTransformer(self.model_name)

            model_registry.register(
                self.model_name,
                self.model
            )

            logger.info("Embedding model loaded successfully")

    @retry(
        stop=stop_after_attempt(settings.MODEL_MAX_RETRIES),
        wait=wait_fixed(2)
    )
    def embed(self, texts: list[str]):
        self.load_model()

        logger.info(f"Generating embeddings for {len(texts)} texts")

        embeddings = self.model.encode(
            texts,
            convert_to_numpy=True
        )

        return embeddings


hf_embedding_client = HFEmbeddingClient()