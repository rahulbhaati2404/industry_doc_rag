from memory.semantic_memory import semantic_memory
from memory.session_memory import session_memory


def build_memory_context(session_id: str, query: str) -> str:
    """Build recent and semantic memory context for prompt construction."""

    history = session_memory.get_recent_history(session_id)
    formatted_history = "\n".join(
        f"{message['role']}: {message['content']}"
        for message in history
    )

    semantic_memories = semantic_memory.recall(
        session_id=session_id,
        query=query,
    )
    semantic_context = "\n".join(semantic_memories)

    return f"""
RECENT CONVERSATION:

{formatted_history}

SEMANTIC MEMORY:

{semantic_context}
"""
