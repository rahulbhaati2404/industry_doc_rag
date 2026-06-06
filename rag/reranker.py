from sentence_transformers import CrossEncoder

from core.config import settings
from core.logger import logger
import asyncio

class Reranker:

    def __init__(self):
        self.model_name = settings.HF_RERANKER_MODEL

        logger.info(
            f"Loading reranker model: {self.model_name}"
        )

        self.model = CrossEncoder(
            self.model_name
        )

        logger.info(
            "Reranker model loaded successfully"
        )

    def rerank(
        self,
        query: str,
        documents: list[dict],
        top_k: int = None
    ):

        if not documents:
            return []

        k = top_k or settings.RERANK_TOP_K

        logger.info(
            f"Reranking {len(documents)} documents"
        )

        pairs = [
            (query, doc["text"])
            for doc in documents
        ]

        scores = self.model.predict(
            pairs
        )

        reranked = []
        for doc, score in zip(documents, scores):
            reranked.append(
                {
                    **doc,
                    "rerank_score": float(score)
                }
            )

        reranked.sort(
            key=lambda x: x["rerank_score"],
            reverse=True
        )

        logger.info(
            f"Returning top {k} reranked documents"
        )

        return reranked[:k]
    
    async def arerank(
        self,
        query: str,
        documents: list
    ):

        return await asyncio.to_thread(
            self.rerank,
            query,
            documents
        )


reranker = Reranker()