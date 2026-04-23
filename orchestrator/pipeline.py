import asyncio
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import AsyncGenerator

from agents.triage import TriageAgent, TriageResult
from agents.image_agent import ImageAgent
from agents.lab_agent import LabAgent
from agents.record_agent import RecordAgent
from agents.diagnosis_agent import DiagnosisAgent
from agents.review_agent import ReviewAgent
from llm import LLMClient
from models import (
    FileType, ExtractionResult, PatientInput,
    ReviewVerdict, ConsultationLog, DebateRound,
)

logger = logging.getLogger(__name__)

# Maximum times LLM A can request sub-agent followup per diagnosis round
MAX_AGENT_REQUERY = 2

# Maximum times triage can ask follow-up questions (0 = skip triage questions)
MAX_TRIAGE_QUESTIONS = 0


class EventType(str, Enum):
    THINKING = "thinking"       # Show loading animation
    STEP_COMPLETE = "step"      # A step finished, show result
    QUESTION = "question"       # Need more info from user
    COMPLETE = "complete"       # Pipeline finished


@dataclass
class PipelineEvent:
    type: EventType
    message: str = ""
    step_name: str = ""
    data: dict = field(default_factory=dict)


class PipelineOrchestrator:
    def __init__(
        self,
        triage: TriageAgent,
        image_agent: ImageAgent,
        lab_agent: LabAgent,
        record_agent: RecordAgent,
        diagnosis_agent: DiagnosisAgent,
        review_agent: ReviewAgent,
        llm: LLMClient,
        vision_llm: LLMClient | None = None,
        max_rounds: int = 3,
    ):
        self.triage = triage
        self.image_agent = image_agent
        self.lab_agent = lab_agent
        self.record_agent = record_agent
        self.diagnosis_agent = diagnosis_agent
        self.review_agent = review_agent
        self.llm = llm
        # vision_llm is used for non-xray image content extraction (e.g. Qwen-VL)
        # Falls back to main llm if not provided
        self.vision_llm = vision_llm or llm
        self.max_rounds = max_rounds

    # ------------------------------------------------------------------
    # Sub-agent followup dispatcher
    # ------------------------------------------------------------------

    async def _run_agent_requests(
        self,
        agent_requests: list,
        extraction: ExtractionResult,
    ) -> str:
        """Dispatch LLM A's requests to sub-agents, return combined results."""
        tasks = []
        labels = []

        for req in agent_requests:
            agent_name = req.agent.lower()
            instruction = req.instruction

            if agent_name == "xray":
                tasks.append(self.image_agent.run_followup(
                    instruction, extraction.xray_findings,
                ))
                labels.append(f"影像Agent")
            elif agent_name == "lab":
                tasks.append(self.lab_agent.run_followup(
                    instruction, extraction.lab_findings,
                ))
                labels.append(f"化验Agent")
            elif agent_name == "record":
                tasks.append(self.record_agent.run_followup(
                    instruction, extraction.record_summaries,
                ))
                labels.append(f"病历Agent")
            else:
                logger.warning("Unknown agent requested: %s", agent_name)

        if not tasks:
            return ""

        results = await asyncio.gather(*tasks)

        parts = []
        for label, result in zip(labels, results):
            parts.append(f"【{label}补充分析】\n{result}")

        return "\n\n".join(parts)

    # ------------------------------------------------------------------
    # Main pipeline
    # ------------------------------------------------------------------

    async def _extract_other_images(self, files: list) -> str:
        """Use vision LLM (e.g. Qwen-VL) to extract content from non-X-ray images."""
        results = []
        for f in files:
            logger.info("Extracting content from image via vision model (%s): %s",
                        self.vision_llm.model, f.original_name)
            text = await self.vision_llm.chat_with_image(
                system_prompt="你是一位专业的医疗信息提取助手。请仔细识别图片中的所有文字和医疗信息，完整地提取出来。",
                user_text="请提取这张图片中的所有文字内容和医疗信息。",
                image_path=f.file_path,
            )
            results.append(f"【{f.original_name}】\n{text}")
        return "\n\n".join(results)

    async def answer_followup(
        self,
        question: str,
        log: ConsultationLog,
        patient: PatientInput,
    ) -> str:
        """Answer a patient's follow-up question after diagnosis is complete."""
        d = log.final_diagnosis
        context = (
            f"患者主诉：{patient.chief_complaint}\n"
            f"过敏史：{patient.allergy_history or '无'}\n"
            f"诊断结论：{d.diagnosis}\n"
            f"置信度：{d.confidence}\n"
            f"诊断依据：{'；'.join(d.evidence_basis)}\n"
            f"治疗建议：{'；'.join(d.treatment_suggestions)}\n"
        )
        messages = [
            {
                "role": "system",
                "content": (
                    "你是一位专业、耐心的主治医师。以下是你刚刚对患者做出的诊断结果。"
                    "现在患者有后续问题想要咨询你。请基于诊断结果，用通俗易懂的语言回答。"
                    "如果问题超出你的诊断范围，请坦诚告知并建议就医。"
                ),
            },
            {
                "role": "user",
                "content": f"## 诊断上下文\n{context}\n\n## 患者提问\n{question}",
            },
        ]
        return await self.llm.chat(messages)

    async def run(
        self,
        chief_complaint: str,
        file_paths: list[str],
        allergy_history: str = "",
        file_tags: dict[str, str] | None = None,
        resume_state: dict | None = None,
    ) -> AsyncGenerator[PipelineEvent, None]:
        """Execute the pipeline, yielding events for real-time UI updates.

        resume_state: if provided, skip triage+extraction and resume diagnosis
        from where the pipeline was paused (when LLM A asked user a question).
        """

        if resume_state:
            # ── Resume from diagnosis (skip triage + extraction) ──────────
            patient        = resume_state["patient"]
            extraction     = resume_state["extraction"]
            other_img_text = resume_state.get("other_img_text", "")
            rounds         = resume_state["rounds"]
            previous_review = resume_state.get("previous_review")
            start_round    = resume_state["round_num"]
            init_sup_info  = resume_state["supplementary_info"]

            # Persist user supplements into patient.chief_complaint so they
            # survive across review rounds (round 2, 3, ...).
            # Then strip them from init_sup_info to avoid sending twice.
            remaining_lines = []
            supplement_lines = []
            for line in init_sup_info.splitlines():
                if "患者补充说明" in line:
                    supplement_lines.append(line)
                else:
                    remaining_lines.append(line)
            if supplement_lines:
                patient.chief_complaint = (
                    f"{patient.chief_complaint}\n\n" + "\n".join(supplement_lines)
                )
            init_sup_info = "\n".join(remaining_lines).strip()

            # ── Process new files uploaded during follow-up ──────────────
            new_file_paths = resume_state.get("new_file_paths", [])
            new_file_tags  = resume_state.get("new_file_tags", {})
            if new_file_paths:
                from models import UploadedFile
                type_map = {
                    "xray": FileType.XRAY,
                    "lab_report": FileType.LAB_REPORT,
                    "medical_record": FileType.MEDICAL_RECORD,
                    "other_image": FileType.OTHER_IMAGE,
                }
                new_xray, new_lab, new_record, new_other = [], [], [], []
                for fp in new_file_paths:
                    name = fp.rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
                    ft = type_map.get(new_file_tags.get(fp, "other_image"), FileType.OTHER_IMAGE)
                    uf = UploadedFile(file_path=fp, file_type=ft, original_name=name)
                    patient.uploaded_files.append(uf)
                    if ft == FileType.XRAY:
                        new_xray.append(uf)
                    elif ft == FileType.LAB_REPORT:
                        new_lab.append(uf)
                    elif ft == FileType.MEDICAL_RECORD:
                        new_record.append(uf)
                    else:
                        new_other.append(uf)

                yield PipelineEvent(
                    type=EventType.THINKING,
                    step_name="extraction",
                    message="正在处理补充上传的文件...",
                )

                gather_tasks = []
                task_labels = []
                if new_xray:
                    gather_tasks.append(self.image_agent.run(new_xray))
                    task_labels.append("xray")
                if new_lab:
                    gather_tasks.append(self.lab_agent.run(new_lab, patient.chief_complaint))
                    task_labels.append("lab")
                if new_record:
                    gather_tasks.append(self.record_agent.run(new_record, patient.chief_complaint))
                    task_labels.append("record")
                if new_other:
                    gather_tasks.append(self._extract_other_images(new_other))
                    task_labels.append("other")

                if gather_tasks:
                    results = await asyncio.gather(*gather_tasks)
                    for label, result in zip(task_labels, results):
                        if label == "xray":
                            extraction.xray_findings.extend(result)
                        elif label == "lab":
                            extraction.lab_findings.extend(result)
                        elif label == "record":
                            extraction.record_summaries.extend(result)
                        elif label == "other" and result:
                            new_img_text = result if isinstance(result, str) else str(result)
                            init_sup_info = (
                                f"{init_sup_info}\n\n【补充图片提取内容】\n{new_img_text}"
                                if init_sup_info else f"【补充图片提取内容】\n{new_img_text}"
                            )

                    yield PipelineEvent(
                        type=EventType.STEP_COMPLETE,
                        step_name="extraction",
                        message="补充文件处理完成。",
                    )

            yield PipelineEvent(
                type=EventType.THINKING,
                step_name="diagnosis",
                message="收到患者补充信息，正在继续诊断推理...",
            )

        else:
            # ========== Step 1: Triage ==========
            yield PipelineEvent(
                type=EventType.THINKING,
                step_name="triage",
                message="正在分析您的主诉和上传文件...",
            )

            triage_result: TriageResult = await self.triage.run(
                chief_complaint=chief_complaint,
                file_paths=file_paths,
                allergy_history=allergy_history,
                file_tags=file_tags,
            )
            patient = triage_result.patient

            file_summary = "\n".join(
                f"  - {f.original_name} → {f.file_type.value}"
                for f in patient.uploaded_files
            )
            yield PipelineEvent(
                type=EventType.STEP_COMPLETE,
                step_name="triage",
                message=f"**分诊完成**\n{file_summary}\n过敏史：{patient.allergy_history or '无'}",
            )

            # Check if triage needs more info (limited by MAX_TRIAGE_QUESTIONS)
            if (MAX_TRIAGE_QUESTIONS > 0
                    and not triage_result.info_sufficient
                    and triage_result.follow_up_questions):
                questions_text = "\n".join(
                    f"{i+1}. {q}" for i, q in enumerate(triage_result.follow_up_questions)
                )
                yield PipelineEvent(
                    type=EventType.QUESTION,
                    step_name="triage",
                    message=f"为了更准确地为您诊断，请补充以下信息：\n\n{questions_text}",
                    data={"questions": triage_result.follow_up_questions},
                )
                return
            elif not triage_result.info_sufficient:
                logger.info("Triage flagged info as insufficient, deferring to LLM A for follow-up")

            # ========== Step 2: Sub-agent extraction (parallel) ==========
            xray_files = [f for f in patient.uploaded_files if f.file_type == FileType.XRAY]
            lab_files = [f for f in patient.uploaded_files if f.file_type == FileType.LAB_REPORT]
            record_files = [f for f in patient.uploaded_files if f.file_type == FileType.MEDICAL_RECORD]
            other_img_files = [f for f in patient.uploaded_files if f.file_type == FileType.OTHER_IMAGE]

            tasks_desc = []
            if xray_files:
                tasks_desc.append(f"影像分析({len(xray_files)}张)")
            if lab_files:
                tasks_desc.append(f"化验单解读({len(lab_files)}份)")
            if record_files:
                tasks_desc.append(f"病历提取({len(record_files)}份)")
            if other_img_files:
                tasks_desc.append(f"图片内容提取({len(other_img_files)}张)")

            other_img_text = ""
            if tasks_desc:
                yield PipelineEvent(
                    type=EventType.THINKING,
                    step_name="extraction",
                    message=f"正在并行处理：{'、'.join(tasks_desc)}...",
                )

                gather_tasks = []
                task_labels = []
                if xray_files:
                    gather_tasks.append(self.image_agent.run(xray_files))
                    task_labels.append("xray")
                if lab_files:
                    gather_tasks.append(self.lab_agent.run(lab_files, chief_complaint))
                    task_labels.append("lab")
                if record_files:
                    gather_tasks.append(self.record_agent.run(record_files, chief_complaint))
                    task_labels.append("record")
                if other_img_files:
                    gather_tasks.append(self._extract_other_images(other_img_files))
                    task_labels.append("other")

                xray_results, lab_results, record_results = [], [], []
                if gather_tasks:
                    results = await asyncio.gather(*gather_tasks, return_exceptions=True)
                    for label, result in zip(task_labels, results):
                        if isinstance(result, BaseException):
                            logger.error("Sub-agent [%s] failed: %s", label, result)
                            continue
                        if label == "xray":
                            xray_results = result
                        elif label == "lab":
                            lab_results = result
                        elif label == "record":
                            record_results = result
                        elif label == "other":
                            other_img_text = result
            else:
                xray_results, lab_results, record_results = [], [], []

            extraction = ExtractionResult(
                xray_findings=xray_results,
                lab_findings=lab_results,
                record_summaries=record_results,
            )

            # Emit extraction results
            if xray_results:
                yield PipelineEvent(
                    type=EventType.STEP_COMPLETE,
                    step_name="xray",
                    message="**影像分析完成 (XrayGLM)**\n" + "\n".join(
                        f"  {f.findings}" for f in xray_results
                    ),
                )
            if lab_results:
                yield PipelineEvent(
                    type=EventType.STEP_COMPLETE,
                    step_name="lab",
                    message="**化验结果提取完成**\n" + "\n".join(
                        f"  {f.summary}" for f in lab_results
                    ),
                )
            if record_results:
                yield PipelineEvent(
                    type=EventType.STEP_COMPLETE,
                    step_name="record",
                    message="**病历摘要提取完成**\n" + "\n".join(
                        f"  {r.key_history}" for r in record_results
                    ),
                )
            if other_img_text:
                yield PipelineEvent(
                    type=EventType.STEP_COMPLETE,
                    step_name="extraction",
                    message=f"**图片内容提取完成**\n{other_img_text[:500]}",
                )
            if not tasks_desc:
                yield PipelineEvent(
                    type=EventType.STEP_COMPLETE,
                    step_name="extraction",
                    message="未检测到可处理的医疗文件，将仅基于主诉进行诊断。",
                )

            # Merge allergies from records
            all_allergies = set()
            if patient.allergy_history:
                all_allergies.add(patient.allergy_history)
            for r in record_results:
                all_allergies.update(r.allergies)
            patient.allergy_history = "；".join(all_allergies) if all_allergies else ""

            # ========== Steps 3-4: Diagnosis + Review loop ==========
            rounds = []
            previous_review = None
            start_round = 1
            init_sup_info = f"【其他图片提取内容】\n{other_img_text}" if other_img_text else ""

        for round_num in range(start_round, self.max_rounds + 1):
            if round_num == start_round:
                supplementary_info = init_sup_info
            else:
                supplementary_info = ""
            agent_requery_count = 0

            # --- Step 3: Diagnosis (with possible info request loop) ---
            while True:
                yield PipelineEvent(
                    type=EventType.THINKING,
                    step_name="diagnosis",
                    message=(
                        f"LLM A 正在进行第{round_num}轮诊断推理..."
                        if not supplementary_info
                        else f"LLM A 收到补充信息，正在重新推理..."
                    ),
                )

                diagnosis = await self.diagnosis_agent.run(
                    patient=patient,
                    extraction=extraction,
                    previous_review=previous_review,
                    supplementary_info=supplementary_info,
                )

                # ---- Handle info requests ----
                if diagnosis.needs_more_info:
                    # Case 1: User questions → pause pipeline
                    if diagnosis.user_questions:
                        questions_text = "\n".join(
                            f"{i+1}. {q}" for i, q in enumerate(diagnosis.user_questions)
                        )
                        reason = ""
                        if diagnosis.reasoning_trace:
                            reason = f"\n\n*（推理过程：{diagnosis.reasoning_trace[:200]}...）*"

                        yield PipelineEvent(
                            type=EventType.STEP_COMPLETE,
                            step_name="diagnosis",
                            message=(
                                f"**LLM A（第{round_num}轮）认为需要更多信息**\n"
                                f"{diagnosis.reasoning_trace[:300] if diagnosis.reasoning_trace else ''}"
                            ),
                        )
                        yield PipelineEvent(
                            type=EventType.QUESTION,
                            step_name="diagnosis",
                            message=(
                                f"主治医师需要您补充以下信息以做出更准确的诊断：\n\n"
                                f"{questions_text}"
                            ),
                            data={
                                "source": "diagnosis",
                                "questions": diagnosis.user_questions,
                                "round": round_num,
                                # Snapshot for resumption — preserves all extracted
                                # data so we don't re-run triage+extraction
                                "resume_state": {
                                    "patient":          patient,
                                    "extraction":       extraction,
                                    "other_img_text":   other_img_text,
                                    "rounds":           rounds,
                                    "round_num":        round_num,
                                    "previous_review":  previous_review,
                                    "supplementary_info": supplementary_info,
                                },
                            },
                        )
                        return  # Pause — wait for user

                    # Case 2: Agent requests only → dispatch and loop back
                    if diagnosis.agent_requests and agent_requery_count < MAX_AGENT_REQUERY:
                        agent_requery_count += 1
                        req_desc = "、".join(
                            f"{r.agent}Agent" for r in diagnosis.agent_requests
                        )
                        yield PipelineEvent(
                            type=EventType.STEP_COMPLETE,
                            step_name="diagnosis",
                            message=(
                                f"**LLM A 请求子Agent补充分析（第{agent_requery_count}次）**\n"
                                + "\n".join(
                                    f"  → {r.agent}Agent：{r.instruction}"
                                    for r in diagnosis.agent_requests
                                )
                            ),
                        )

                        yield PipelineEvent(
                            type=EventType.THINKING,
                            step_name="extraction",
                            message=f"子Agent（{req_desc}）正在执行补充分析...",
                        )

                        new_info = await self._run_agent_requests(
                            diagnosis.agent_requests, extraction,
                        )

                        yield PipelineEvent(
                            type=EventType.STEP_COMPLETE,
                            step_name="extraction",
                            message=f"**子Agent补充分析完成**\n{new_info[:500]}",
                        )

                        # Accumulate supplementary info
                        supplementary_info = (
                            f"{supplementary_info}\n\n{new_info}" if supplementary_info else new_info
                        )
                        continue  # Loop back to LLM A with new info

                    # Fallback: max requery reached or no actionable requests
                    if agent_requery_count >= MAX_AGENT_REQUERY:
                        logger.info("Max agent re-queries reached, proceeding with current info")

                # LLM A is satisfied (or we forced it) → proceed to review
                break

            yield PipelineEvent(
                type=EventType.STEP_COMPLETE,
                step_name="diagnosis",
                message=(
                    f"**LLM A 诊断结论（第{round_num}轮）**\n"
                    f"诊断：{diagnosis.diagnosis}\n"
                    f"置信度：{diagnosis.confidence}\n"
                    f"治疗建议：\n" + "\n".join(f"  - {s}" for s in diagnosis.treatment_suggestions)
                ),
                data={"round": round_num},
            )

            # --- Step 4: Review ---
            yield PipelineEvent(
                type=EventType.THINKING,
                step_name="review",
                message=f"LLM B 正在审核第{round_num}轮诊断...",
            )

            review = await self.review_agent.run(
                diagnosis=diagnosis,
                patient=patient,
                extraction=extraction,
                round_number=round_num,
                supplementary_info=supplementary_info,
            )

            rounds.append(DebateRound(diagnosis=diagnosis, review=review))

            if review.verdict == ReviewVerdict.APPROVED:
                yield PipelineEvent(
                    type=EventType.STEP_COMPLETE,
                    step_name="review_pass",
                    message=f"**LLM B 审核通过（第{round_num}轮）**\n{review.comments}",
                    data={"round": round_num},
                )
                break
            else:
                issues = []
                if review.safety_issues:
                    issues.append("安全性问题：\n" + "\n".join(f"  - {s}" for s in review.safety_issues))
                if review.logic_issues:
                    issues.append("逻辑性问题：\n" + "\n".join(f"  - {s}" for s in review.logic_issues))

                yield PipelineEvent(
                    type=EventType.STEP_COMPLETE,
                    step_name="review_reject",
                    message=(
                        f"**LLM B 审核驳回（第{round_num}轮）**\n"
                        f"{review.comments}\n" + "\n".join(issues)
                    ),
                    data={"round": round_num},
                )

                if round_num < self.max_rounds:
                    yield PipelineEvent(
                        type=EventType.THINKING,
                        step_name="retry",
                        message=f"返回 LLM A 进行第{round_num + 1}轮修正...",
                    )
                else:
                    yield PipelineEvent(
                        type=EventType.STEP_COMPLETE,
                        step_name="max_rounds",
                        message="已达最大博弈轮数，将输出当前诊断结果（附风险标注）。",
                    )

                previous_review = review

        # ========== Step 5: Final output ==========
        final_diagnosis = rounds[-1].diagnosis
        approved = rounds[-1].review.verdict == ReviewVerdict.APPROVED

        log = ConsultationLog(
            rounds=rounds,
            final_diagnosis=final_diagnosis,
            total_rounds=len(rounds),
            approved=approved,
        )

        yield PipelineEvent(
            type=EventType.COMPLETE,
            message="会诊完成",
            data={"log": log, "patient": patient},
        )
