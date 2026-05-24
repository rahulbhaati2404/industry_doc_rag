import chromadb

from core.config import settings
from core.logger import logger

from rag.embedder import document_embedder
from cache.cache_manager import cache_manager
from cache.semantic_cache import semantic_cache


class SemanticMemory:

    def __init__(self):

        self.client = chromadb.PersistentClient(
            path=settings.CHROMA_PERSIST_DIR
        )

        self.collection = (
            self.client.get_or_create_collection(
                name="semantic_memory"
            )
        )

    def remember(
        self,
        session_id: str,
        memory: str
    ) -> None:

        logger.info(
            "Storing semantic memory"
        )

        embedding = document_embedder.embed_query(
            memory
        )

        self.collection.add(
            ids=[
                f"{session_id}_{hash(memory)}"
            ],
            documents=[memory],
            metadatas=[
                {
                    "session_id": session_id
                }
            ],
            embeddings=[
                embedding.tolist()
            ]
        )

        cache_manager.invalidate_sync("semantic:")

    def recall(
        self,
        session_id: str,
        query: str,
        top_k: int = 3
    ) -> list[str]:

        logger.info(
            "Recalling semantic memory"
        )

        cached = semantic_cache.get_sync(
            session_id=session_id,
            query=query,
            top_k=top_k,
        )
        if cached is not None:
            logger.info("Semantic memory cache hit")
            return cached

        embedding = document_embedder.embed_query(
            query
        )

        results = self.collection.query(
            query_embeddings=[
                embedding.tolist()
            ],
            n_results=top_k,
            where={
                "session_id": session_id
            }
        )

        memories = results["documents"][0]

        semantic_cache.set_sync(
            session_id=session_id,
            query=query,
            top_k=top_k,
            memories=memories,
        )

        return memories


semantic_memory = SemanticMemory()
