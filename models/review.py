from enum import Enum

from pydantic import BaseModel

from .diagnosis import DiagnosisResult


class ReviewVerdict(str, Enum):
    APPROVED = "approved"
    REJECTED = "rejected"


class ReviewResult(BaseModel):
    verdict: ReviewVerdict
    safety_issues: list[str] = []
    logic_issues: list[str] = []
    comments: str = ""
    round_number: int = 1


class DebateRound(BaseModel):
    diagnosis: DiagnosisResult
    review: ReviewResult


class ConsultationLog(BaseModel):
    rounds: list[DebateRound] = []
    final_diagnosis: DiagnosisResult | None = None
    total_rounds: int = 0
    approved: bool = False
