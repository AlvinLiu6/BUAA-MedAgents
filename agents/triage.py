import logging
from pathlib import Path

from .base import BaseAgent
from llm import LLMClient
from models import PatientInput, UploadedFile, FileType

logger = logging.getLogger(__name__)

PROMPT_TEMPLATE = (Path(__file__).parent.parent / "prompts" / "triage.txt").read_text(
    encoding="utf-8"
)


class TriageResult:
    """Triage result that may indicate more info is needed."""

    def __init__(
        self,
        patient: PatientInput,
        info_sufficient: bool = True,
        follow_up_questions: list[str] | None = None,
        intent_summary: str = "",
    ):
        self.patient = patient
        self.info_sufficient = info_sufficient
        self.follow_up_questions = follow_up_questions or []
        self.intent_summary = intent_summary


class TriageAgent(BaseAgent):
    def __init__(self, llm: LLMClient):
        super().__init__("TriageAgent")
        self.llm = llm

    async def run(
        self,
        chief_complaint: str,
        file_paths: list[str],
        allergy_history: str = "",
        file_tags: dict[str, str] | None = None,
    ) -> TriageResult:
        """Run triage. file_tags maps file_path -> tag string (e.g. 'xray')."""
        file_tags = file_tags or {}

        # Files that need LLM classification (no user tag)
        untagged_paths = [fp for fp in file_paths if fp not in file_tags]

        file_list = "\n".join(
            f"- {Path(fp).name}" for fp in untagged_paths
        ) or "无上传文件"

        prompt = PROMPT_TEMPLATE.format(
            chief_complaint=chief_complaint,
            file_list=file_list,
            allergy_history=allergy_history or "未提供",
        )

        messages = [
            {"role": "system", "content": "你是一位专业的医疗分诊助手，请以JSON格式返回结果。"},
            {"role": "user", "content": prompt},
        ]

        result = await self.llm.chat_json(messages)
        logger.info("Triage result: %s", result.get("intent_summary", ""))

        # Build typed file list
        type_map = {
            "xray": FileType.XRAY,
            "lab_report": FileType.LAB_REPORT,
            "medical_record": FileType.MEDICAL_RECORD,
            "other_image": FileType.OTHER_IMAGE,
        }
        classifications = {
            item["file_name"]: item["file_type"]
            for item in result.get("file_classifications", [])
        }

        uploaded_files = []
        for fp in file_paths:
            name = Path(fp).name
            if fp in file_tags:
                # User-provided tag takes priority
                ft = type_map.get(file_tags[fp], FileType.UNKNOWN)
            else:
                ft_str = classifications.get(name, "unknown")
                ft = type_map.get(ft_str, FileType.UNKNOWN)
            uploaded_files.append(UploadedFile(
                file_path=fp,
                file_type=ft,
                original_name=name,
            ))

        # Merge allergy info
        extracted_allergies = result.get("extracted_allergies", "")
        combined_allergies = allergy_history
        if extracted_allergies:
            combined_allergies = f"{allergy_history}；{extracted_allergies}" if allergy_history else extracted_allergies

        patient = PatientInput(
            chief_complaint=chief_complaint,
            uploaded_files=uploaded_files,
            allergy_history=combined_allergies,
        )

        return TriageResult(
            patient=patient,
            info_sufficient=result.get("info_sufficient", True),
            follow_up_questions=result.get("follow_up_questions", []),
            intent_summary=result.get("intent_summary", ""),
        )
