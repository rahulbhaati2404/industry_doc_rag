from core.config import settings
from core.logger import logger
from observability.tracing import trace_manager

async def validate_answer(
    query: str,
    context: str,
    answer: str,
    model: str,
) -> tuple[str, float, bool, bool, str | None, str | None]:
    """Run hallucination detection, mitigation, and output guardrails."""

    from guardrails.output_guard import output_guard
    from hallucination.detector import hallucination_detector
    from hallucination.mitigator import hallucination_mitigator

    with trace_manager.trace("hallucination_detection"):
        hallucination_result = await hallucination_detector.aevaluate(
            query=query,
            context=context,
            answer=answer,
        )

    confidence_score = hallucination_result["score"]
    is_hallucinated = hallucination_result["is_hallucinated"]
    attempts = 0

    while is_hallucinated and attempts < settings.MAX_REGENERATION_ATTEMPTS:
        logger.warning(f"Hallucination detected. Regeneration attempt {attempts + 1}")
        answer = hallucination_mitigator.regenerate(
            query=query,
            context=context,
            model=model,
        )
        hallucination_result = await hallucination_detector.aevaluate(
            query=query,
            context=context,
            answer=answer,
        )
        confidence_score = hallucination_result["score"]
        is_hallucinated = hallucination_result["is_hallucinated"]
        attempts += 1

    if is_hallucinated:
        logger.error("Hallucination mitigation failed")
        answer = (
            "I could not confidently generate a grounded answer "
            "from the provided documents."
        )

    output_result = output_guard.validate_output(answer)
    return (
        output_result.cleaned_text or answer,
        confidence_score,
        is_hallucinated,
        output_result.blocked,
        output_result.message,
        output_result.matched_pattern,
    )
