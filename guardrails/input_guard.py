import re

from core.config import settings
from core.logger import logger

from context.token_counter import (
    token_counter
)


class InputGuard:

    INJECTION_PATTERNS = [
        r"ignore previous instructions",
        r"system prompt",
        r"reveal hidden prompt",
        r"bypass restrictions",
        r"developer mode",
        r"jailbreak",
        r"pretend you are"
    ]

    PII_PATTERNS = {
        "EMAIL": r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+",
        "PHONE": r"\+?\d[\d -]{8,}\d",
        "CREDIT_CARD": r"\b\d{13,16}\b"
    }

    def validate_input(
        self,
        query: str
    ):

        logger.info(
            "Running input guardrails"
        )

        # TOKEN LIMIT
        token_count = (
            token_counter.estimate_tokens(query)
        )

        if token_count > settings.MAX_INPUT_TOKENS:

            raise ValueError(
                "Input exceeds token limit"
            )

        # PROMPT INJECTION
        if (
            settings
            .ENABLE_PROMPT_INJECTION_DETECTION
        ):

            lowered = query.lower()

            for pattern in (
                self.INJECTION_PATTERNS
            ):

                if re.search(
                    pattern,
                    lowered
                ):

                    logger.warning(
                        f"Prompt injection detected: "
                        f"{pattern}"
                    )

                    raise ValueError(
                        "Potential prompt injection detected"
                    )

        # PII MASKING
        if settings.ENABLE_PII_MASKING:

            for pii_type, pattern in (
                self.PII_PATTERNS.items()
            ):

                query = re.sub(
                    pattern,
                    f"[REDACTED_{pii_type}]",
                    query
                )

        return query


input_guard = InputGuard()