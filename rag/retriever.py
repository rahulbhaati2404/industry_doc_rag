from core.logger import logger

from rag.vector_store import vector_store
from rag.reranker import reranker
from observability.metrics import (
    metrics_collector
)

from observability.tracing import (
    trace_manager
)
from cache.retrieval_cache import retrieval_cache

import asyncio

class Retriever:

    def retrieve(
        self,
        query: str,
        top_k: int = 5
    ) -> list[dict]:

        logger.info(
            f"Running retrieval for query: {query}"
        )

        cached = retrieval_cache.get_sync(
            query=query,
            top_k=top_k
        )

        if cached is not None:
            logger.info("Retrieval cache hit")
            return cached

        with trace_manager.trace(
            "retrieval"
        ):

            raw_results = (
                vector_store.similarity_search(
                    query=query,
                    top_k=top_k
                )
            )

        documents = []

        for i in range(
            len(raw_results["documents"][0])
        ):

            documents.append(
                {
                    "text": raw_results["documents"][0][i],
                    "metadata": raw_results["metadatas"][0][i]
                }
            )

        logger.info(
            f"Retrieved {len(documents)} candidate documents"
        )

        reranked_docs = reranker.rerank(
            query=query,
            documents=documents
        )

        for idx, doc in enumerate(reranked_docs):
            logger.info(
                f"Rank {idx+1} | "
                f"Score={doc['rerank_score']:.4f} | "
                f"Source={doc['metadata'].get('source')}"
            )

        logger.info(
            f"Final reranked docs count: {len(reranked_docs)}"
        )

        metrics_collector.record(
            "retrieved_documents",
            len(reranked_docs)
        )

        if reranked_docs:
            metrics_collector.record(
                "top_rerank_score",
                reranked_docs[0]["rerank_score"]
            )

        retrieval_cache.set_sync(
            query=query,
            top_k=top_k,
            documents=reranked_docs
        )

        return reranked_docs
    
    async def aretrieve(
        self,
        query: str,
        top_k: int = 5
    ) -> list[dict]:

        return await asyncio.to_thread(

            self.retrieve,

            query,

            top_k
        )


retriever = Retriever()
