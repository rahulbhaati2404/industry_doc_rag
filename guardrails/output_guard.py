import re

from core.logger import logger


class OutputGuard:

    BLOCKED_PATTERNS = [
        r"hate speech",
        r"violent extremism",
        r"social security number",
        r"credit card number"
    ]

    def validate_output(
        self,
        response: str
    ):

        logger.info(
            "Running output guardrails"
        )

        lowered = response.lower()

        for pattern in (
            self.BLOCKED_PATTERNS
        ):

            if re.search(
                pattern,
                lowered
            ):

                logger.warning(
                    f"Unsafe output detected: "
                    f"{pattern}"
                )

                return (
                    "Response blocked due to "
                    "safety policy."
                )

        return response


output_guard = OutputGuard()