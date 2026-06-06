from memory.semantic_memory import semantic_memory
from memory.session_memory import session_memory
import re


def _compact_lines(text: str) -> str:
    lines = [
        line.strip()
        for line in text.splitlines()
        if line.strip()
    ]
    return " ".join(lines)


def _extract_identity_from_history(history: list[dict]) -> str | None:
    for message in reversed(history):
        if message.get("role") != "user":
            continue

        content = message.get("content", "")
        match = re.search(
            r"\b(?:i am|i'm|my name is|call me)\s+([A-Za-z][A-Za-z '\-]{1,80})",
            content,
            flags=re.IGNORECASE,
        )
        if match:
            return match.group(1).strip().rstrip(".,!?")

    return None


def is_memory_reliant_query(query: str) -> bool:
    lowered = query.strip().lower()
    memory_intent_patterns = [
        r"\bwho am i\b",
        r"\bwhat am i\b",
        r"\bwhat is my name\b",
        r"\bwhat's my name\b",
        r"\btell me about me\b",
        r"\bdo you remember me\b",
        r"\bwhat did i say\b",
        r"\bwhat was my name\b",
    ]

    return any(re.search(pattern, lowered) for pattern in memory_intent_patterns)


def resolve_memory_answer(session_id: str, query: str) -> str | None:
    history = session_memory.get_recent_history(session_id)

    if not is_memory_reliant_query(query):
        return None

    identity = _extract_identity_from_history(history)
    if identity:
        return f"You told me your name is {identity}."

    semantic_memories = semantic_memory.recall(
        session_id=session_id,
        query=query,
    )
    semantic_identity = _extract_identity_from_history(
        [
            {
                "role": "user",
                "content": memory,
            }
            for memory in semantic_memories
        ]
    )
    if semantic_identity:
        return f"You told me your name is {semantic_identity}."

    return None


def build_retrieval_query(session_id: str, query: str) -> str:
    history = session_memory.get_recent_history(session_id)
    recent_history = _compact_lines(
        "\n".join(
            f"{message['role']}: {message['content']}"
            for message in history
        )
    )

    semantic_memories = semantic_memory.recall(
        session_id=session_id,
        query=query,
    )
    semantic_context = _compact_lines("\n".join(semantic_memories))

    context_parts = [query]
    if recent_history:
        context_parts.append(f"Recent conversation: {recent_history}")
    if semantic_context:
        context_parts.append(f"Semantic memory: {semantic_context}")

    return " ".join(context_parts)


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
