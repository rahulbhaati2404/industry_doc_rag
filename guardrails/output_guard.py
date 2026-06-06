import re

from core.logger import logger
from guardrails.decision import GuardrailDecision


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
    ) -> GuardrailDecision:

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

                return GuardrailDecision(
                    blocked=True,
                    message=(
                        "I cannot provide that answer because it "
                        "matches a restricted safety pattern. "
                        "Please rephrase the request."
                    ),
                    cleaned_text=(
                        "I cannot provide that answer because it "
                        "matches a restricted safety pattern. "
                        "Please rephrase the request."
                    ),
                    matched_pattern=pattern,
                )

        return GuardrailDecision(
            blocked=False,
            cleaned_text=response,
        )


output_guard = OutputGuard()
