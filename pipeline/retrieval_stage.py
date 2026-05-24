from observability.tracing import trace_manager


async def run_retrieval(query: str) -> list[dict]:
    """Run the existing retriever behind a pipeline stage boundary."""

    from rag.retriever import retriever

    with trace_manager.trace("retrieval"):
        return await retriever.aretrieve(query=query)
