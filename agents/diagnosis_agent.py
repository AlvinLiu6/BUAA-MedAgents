import json
import logging
from pathlib import Path

from .base import BaseAgent
from llm import LLMClient
from models import PatientInput, ExtractionResult, DiagnosisResult, ReviewResult
from models.diagnosis import AgentRequest

logger = logging.getLogger(__name__)

PROMPT_TEMPLATE = (Path(__file__).parent.parent / "prompts" / "diagnosis.txt").read_text(
    encoding="utf-8"
)


class DiagnosisAgent(BaseAgent):
    """LLM A: 综合诊断Agent，具备向用户/子Agent请求更多信息的能力。"""

    def __init__(self, llm: LLMClient):
        super().__init__("DiagnosisAgent")
        self.llm = llm

    async def run(
        self,
        patient: PatientInput,
        extraction: ExtractionResult,
        previous_review: ReviewResult | None = None,
        supplementary_info: str = "",
    ) -> DiagnosisResult:
        # Format extraction data
        xray_text = "\n".join(
            f"[{f.image_path}]\n{f.findings}" for f in extraction.xray_findings
        ) or "无影像检查数据"

        lab_text = "\n".join(
            f"[{f.source_file}] {f.summary}\n异常指标：{json.dumps(f.abnormal_indicators, ensure_ascii=False)}"
            for f in extraction.lab_findings
        ) or "无化验检查数据"

        record_text = "\n".join(
            f"[{r.source_file}] {r.key_history}\n"
            f"过敏史：{', '.join(r.allergies) or '无'}\n"
            f"当前用药：{', '.join(r.current_medications) or '无'}\n"
            f"既往诊断：{', '.join(r.past_diagnoses) or '无'}"
            for r in extraction.record_summaries
        ) or "无病历数据"

        # Format review feedback if this is a retry
        review_feedback = ""
        if previous_review:
            issues = []
            if previous_review.safety_issues:
                issues.append("安全性问题：\n" + "\n".join(f"- {s}" for s in previous_review.safety_issues))
            if previous_review.logic_issues:
                issues.append("逻辑性问题：\n" + "\n".join(f"- {s}" for s in previous_review.logic_issues))
            review_feedback = (
                f"\n## ⚠️ 上一轮审核意见（第{previous_review.round_number}轮被驳回）：\n"
                f"{previous_review.comments}\n\n"
                + "\n".join(issues)
                + "\n\n请针对以上问题进行修正，重新给出诊断和治疗方案。"
            )

        # Format supplementary info from sub-agent re-queries
        sup_section = ""
        if supplementary_info:
            sup_section = f"\n## 补充信息（由子Agent/患者补充）：\n{supplementary_info}"

        prompt = PROMPT_TEMPLATE.format(
            chief_complaint=patient.chief_complaint,
            allergy_history=patient.allergy_history or "未提供",
            xray_findings=xray_text,
            lab_findings=lab_text,
            record_summaries=record_text,
            review_feedback=review_feedback,
            supplementary_info=sup_section,
        )

        messages = [
            {"role": "system", "content": "你是一位经验丰富的主治医师，请基于所有信息进行综合诊断。以JSON格式返回。"},
            {"role": "user", "content": prompt},
        ]

        data = await self.llm.chat_json(messages)

        needs_more = data.get("needs_more_info", False)

        # Parse agent requests
        agent_requests = []
        for req in data.get("agent_requests", []):
            if isinstance(req, dict) and req.get("agent") and req.get("instruction"):
                agent_requests.append(AgentRequest(
                    agent=req["agent"],
                    instruction=req["instruction"],
                ))

        result = DiagnosisResult(
            diagnosis=data.get("diagnosis", ""),
            confidence=data.get("confidence", "low"),
            evidence_basis=data.get("evidence_basis", []),
            treatment_suggestions=data.get("treatment_suggestions", []),
            reasoning_trace=data.get("reasoning_trace", ""),
            needs_more_info=needs_more,
            user_questions=data.get("user_questions", []),
            agent_requests=agent_requests,
        )

        if needs_more:
            logger.info(
                "Diagnosis needs more info: user_questions=%d, agent_requests=%d",
                len(result.user_questions), len(result.agent_requests),
            )
        else:
            logger.info("Diagnosis: %s (confidence: %s)", result.diagnosis, result.confidence)

        return result
