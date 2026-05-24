from observability.tracing import trace_manager


async def run_rerank(query: str, documents: list[dict]) -> list[dict]:
    """Run semantic reranking for retrieved documents."""

    from rag.reranker import reranker

    with trace_manager.trace("reranking"):
        return await reranker.arerank(query=query, documents=documents)
