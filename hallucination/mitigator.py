from core.config import settings
from core.logger import logger

from models.ollama_client import ollama_client


class HallucinationMitigator:

    STRICT_PROMPT = """
        You must answer ONLY from the provided context.

        Do NOT use outside knowledge.

        If the answer is not explicitly present,
        say:

        "I could not find enough information in the provided documents."
    """

    def regenerate(
        self,
        query: str,
        context: str,
        model: str
    ):

        logger.warning(
            "Attempting hallucination mitigation regeneration"
        )

        prompt = f"""
            {self.STRICT_PROMPT}

            CONTEXT:
            {context}

            QUESTION:
            {query}

            ANSWER:
        """

        response = ollama_client.generate(
            prompt=prompt,
            model=model,
            temperature=0.0
        )

        return response


hallucination_mitigator = (
    HallucinationMitigator()
)