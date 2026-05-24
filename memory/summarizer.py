from models.ollama_client import (
    ollama_client
)

from core.logger import logger


class ConversationSummarizer:

    SUMMARY_PROMPT = """
    Summarize the important conversation context.

    Focus on:
    - user goals
    - technical topics
    - decisions
    - preferences
    - unresolved questions

    Keep summary concise.
    """

    def summarize(
        self,
        conversation: list[dict]
    ):

        logger.info(
            "Generating conversation summary"
        )

        formatted = "\n".join(

            f"{m['role']}: {m['content']}"

            for m in conversation
        )

        prompt = f"""
        {self.SUMMARY_PROMPT}

        CONVERSATION:

        {formatted}

        SUMMARY:
        """

        summary = ollama_client.generate(
            prompt=prompt,
            model="llama3.2:1b"
        )

        return summary


conversation_summarizer = (
    ConversationSummarizer()
)