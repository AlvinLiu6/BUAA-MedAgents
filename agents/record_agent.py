import logging
from pathlib import Path

from .base import BaseAgent
from llm import LLMClient
from models import UploadedFile, RecordSummary

logger = logging.getLogger(__name__)

PROMPT_TEMPLATE = (Path(__file__).parent.parent / "prompts" / "record_extraction.txt").read_text(
    encoding="utf-8"
)


class RecordAgent(BaseAgent):
    def __init__(self, llm: LLMClient, vision_llm: LLMClient | None = None):
        super().__init__("RecordAgent")
        self.llm = llm
        self.vision_llm = vision_llm or llm

    async def run(
        self,
        record_files: list[UploadedFile],
        chief_complaint: str = "",
    ) -> list[RecordSummary]:
        results = []
        for f in record_files:
            logger.info("Extracting medical record: %s", f.original_name)
            prompt = PROMPT_TEMPLATE.format(chief_complaint=chief_complaint or "未提供")

            suffix = Path(f.file_path).suffix.lower()
            if suffix in (".png", ".jpg", ".jpeg", ".bmp", ".tiff"):
                data = await self.vision_llm.chat_with_image_json(
                    system_prompt="你是一位专业的病案管理医师，请以JSON格式返回病历提取结果。",
                    user_text=prompt,
                    image_path=f.file_path,
                )
            else:
                try:
                    content = Path(f.file_path).read_text(encoding="utf-8")
                except Exception:
                    content = "无法读取文件内容"

                messages = [
                    {"role": "system", "content": "你是一位专业的病案管理医师，请以JSON格式返回病历提取结果。"},
                    {"role": "user", "content": f"{prompt}\n\n病历内容：\n{content}"},
                ]
                data = await self.llm.chat_json(messages)

            results.append(RecordSummary(
                source_file=f.original_name,
                key_history=data.get("key_history", ""),
                allergies=data.get("allergies", []),
                current_medications=data.get("current_medications", []),
                past_diagnoses=data.get("past_diagnoses", []),
            ))

        return results

    async def run_followup(
        self,
        instruction: str,
        existing_summaries: list[RecordSummary],
    ) -> str:
        """根据 LLM A 的指令，对已有病历做针对性补充分析。"""
        if not existing_summaries:
            return "无可用的病历数据，无法执行补充分析。"

        context = "\n".join(
            f"[{r.source_file}] {r.key_history}\n"
            f"过敏史：{', '.join(r.allergies) or '无'}\n"
            f"当前用药：{', '.join(r.current_medications) or '无'}\n"
            f"既往诊断：{', '.join(r.past_diagnoses) or '无'}"
            for r in existing_summaries
        )

        messages = [
            {
                "role": "system",
                "content": (
                    "你是一位病案管理医师。以下是之前对病历的提取结果。"
                    "请根据主治医师的具体指令，做更深入的针对性分析。"
                ),
            },
            {
                "role": "user",
                "content": (
                    f"## 已有病历摘要\n{context}\n\n"
                    f"## 主治医师指令\n{instruction}\n\n"
                    "请给出针对性的补充分析。"
                ),
            },
        ]
        return await self.llm.chat(messages)
