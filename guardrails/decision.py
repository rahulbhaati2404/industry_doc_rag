from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class GuardrailDecision:
    blocked: bool
    message: Optional[str] = None
    cleaned_text: Optional[str] = None
    matched_pattern: Optional[str] = None
