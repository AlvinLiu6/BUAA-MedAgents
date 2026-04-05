from .patient import PatientInput, UploadedFile, FileType
from .agent_output import XrayFindings, LabFindings, RecordSummary, ExtractionResult
from .diagnosis import DiagnosisResult, AgentRequest
from .review import ReviewResult, ReviewVerdict, ConsultationLog, DebateRound

__all__ = [
    "PatientInput", "UploadedFile", "FileType",
    "XrayFindings", "LabFindings", "RecordSummary", "ExtractionResult",
    "DiagnosisResult", "AgentRequest",
    "ReviewResult", "ReviewVerdict", "ConsultationLog", "DebateRound",
]
