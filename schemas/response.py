from pydantic import BaseModel
from typing import Optional

class SourceChunk(BaseModel):
    content: str
    source_file: str
    relevance_score: float


class TokenUsage(BaseModel):
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    
class QueryResponse(BaseModel):
    query: str
    answer: str
    model_used: str

    sources: list[SourceChunk]

    tokens_used: TokenUsage

    latency_ms: float

    confidence_score: Optional[float] = None

    is_hallucinated: bool = False

    status: str = "success"
    message: Optional[str] = None
    guardrail_triggered: bool = False
    guardrail_reason: Optional[str] = None
