from transformers import pipeline
from core.config import settings
from core.logger import logger
import asyncio


class HallucinationDetector:

    def __init__(self):

        logger.info(
            f"Loading hallucination model: "
            f"{settings.HF_HALLUCINATION_MODEL}"
        )

        self.detector = pipeline(
            "text-classification",
            model=settings.HF_HALLUCINATION_MODEL
        )

        logger.info(
            "Hallucination detector loaded"
        )

    def evaluate(
        self,
        query: str,
        context: str,
        answer: str
    ):

        premise = context[:3000]
        hypothesis = answer

        result = self.detector(
            {
                "text": premise,
                "text_pair": hypothesis
            }
        )

        if isinstance(result, list):
            result = result[0]

        label = result["label"]
        score = float(result["score"])

        logger.info(
            f"NLI label={label} "
            f"score={score:.4f}"
        )

        is_hallucinated = (
            label.upper() == "CONTRADICTION"
        )

        if is_hallucinated:
            confidence_score = 1.0 - score
        else:
            confidence_score = score

        return {
            "score": confidence_score,
            "label": label,
            "is_hallucinated": is_hallucinated
        }

    async def aevaluate(
        self,
        query: str,
        context: str,
        answer: str
    ):

        return await asyncio.to_thread(
            self.evaluate,
            query,
            context,
            answer
        )    


hallucination_detector = (
    HallucinationDetector()
)