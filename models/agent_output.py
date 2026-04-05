from pydantic import BaseModel


class XrayFindings(BaseModel):
    image_path: str
    findings: str
    abnormalities: list[str] = []


class LabFindings(BaseModel):
    source_file: str
    abnormal_indicators: list[dict] = []
    summary: str = ""


class RecordSummary(BaseModel):
    source_file: str
    key_history: str = ""
    allergies: list[str] = []
    current_medications: list[str] = []
    past_diagnoses: list[str] = []


class ExtractionResult(BaseModel):
    xray_findings: list[XrayFindings] = []
    lab_findings: list[LabFindings] = []
    record_summaries: list[RecordSummary] = []
