from enum import Enum

from pydantic import BaseModel


class FileType(str, Enum):
    XRAY = "xray"
    LAB_REPORT = "lab_report"
    MEDICAL_RECORD = "medical_record"
    OTHER_IMAGE = "other_image"
    UNKNOWN = "unknown"


class UploadedFile(BaseModel):
    file_path: str
    file_type: FileType = FileType.UNKNOWN
    original_name: str = ""


class PatientInput(BaseModel):
    chief_complaint: str
    uploaded_files: list[UploadedFile] = []
    allergy_history: str = ""
