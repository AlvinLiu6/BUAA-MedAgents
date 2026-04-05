import json
import logging
from pathlib import Path

from .base import BaseAgent
from llm import LLMClient
from models import (
    PatientInput, ExtractionResult, DiagnosisResult,
    ReviewResult, ReviewVerdict,
)

logger = logging.getLogger(__name__)

PROMPT_TEMPLATE = (Path(__file__).parent.parent / "prompts" / "review.txt").read_text(
    encoding="utf-8"
)


class ReviewAgent(BaseAgent):
    """LLM B: 诊断审核Agent"""

    def __init__(self, llm: LLMClient):
        super().__init__("ReviewAgent")
        self.llm = llm

    async def run(
        self,
        diagnosis: DiagnosisResult,
        patient: PatientInput,
        extraction: ExtractionResult,
        round_number: int = 1,
        supplementary_info: str = "",
    ) -> ReviewResult:
        xray_text = "\n".join(
            f"[{f.image_path}]\n{f.findings}" for f in extraction.xray_findings
        ) or "无影像检查数据"

        lab_text = "\n".join(
            f"[{f.source_file}] {f.summary}\n异常指标：{json.dumps(f.abnormal_indicators, ensure_ascii=False)}"
            for f in extraction.lab_findings
        ) or "无化验检查数据"

        record_text = "\n".join(
            f"[{r.source_file}] {r.key_history}" for r in extraction.record_summaries
        ) or "无病历数据"

        prompt = PROMPT_TEMPLATE.format(
            chief_complaint=patient.chief_complaint,
            allergy_history=patient.allergy_history or "未提供",
            xray_findings=xray_text,
            lab_findings=lab_text,
            record_summaries=record_text,
            supplementary_info=supplementary_info,
            diagnosis=diagnosis.diagnosis,
            confidence=diagnosis.confidence,
            evidence_basis=json.dumps(diagnosis.evidence_basis, ensure_ascii=False),
            treatment_suggestions=json.dumps(diagnosis.treatment_suggestions, ensure_ascii=False),
            reasoning_trace=diagnosis.reasoning_trace,
        )

        messages = [
            {"role": "system", "content": "你是一位严谨的医疗质控审核医师，请严格审核诊断方案。以JSON格式返回。"},
            {"role": "user", "content": prompt},
        ]

        data = await self.llm.chat_json(messages)

        verdict_str = data.get("verdict", "rejected").lower()
        verdict = ReviewVerdict.APPROVED if verdict_str == "approved" else ReviewVerdict.REJECTED

        result = ReviewResult(
            verdict=verdict,
            safety_issues=data.get("safety_issues", []),
            logic_issues=data.get("logic_issues", []),
            comments=data.get("comments", ""),
            round_number=round_number,
        )

        logger.info(
            "Review round %d: %s (safety_issues=%d, logic_issues=%d)",
            round_number, verdict.value,
            len(result.safety_issues), len(result.logic_issues),
        )
        return result
