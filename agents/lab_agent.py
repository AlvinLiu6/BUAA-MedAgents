import json
import logging
from pathlib import Path

from .base import BaseAgent
from llm import LLMClient
from models import UploadedFile, LabFindings

logger = logging.getLogger(__name__)

PROMPT_TEMPLATE = (Path(__file__).parent.parent / "prompts" / "lab_extraction.txt").read_text(
    encoding="utf-8"
)


class LabAgent(BaseAgent):
    def __init__(self, llm: LLMClient, vision_llm: LLMClient | None = None):
        super().__init__("LabAgent")
        self.llm = llm
        self.vision_llm = vision_llm or llm

    async def run(
        self,
        lab_files: list[UploadedFile],
        chief_complaint: str = "",
    ) -> list[LabFindings]:
        results = []
        for f in lab_files:
            logger.info("Extracting lab report: %s", f.original_name)
            prompt = PROMPT_TEMPLATE.format(chief_complaint=chief_complaint or "未提供")

            suffix = Path(f.file_path).suffix.lower()
            if suffix in (".png", ".jpg", ".jpeg", ".bmp", ".tiff"):
                data = await self.vision_llm.chat_with_image_json(
                    system_prompt="你是一位专业的检验科医师，请以JSON格式返回化验单分析结果。",
                    user_text=prompt,
                    image_path=f.file_path,
                )
            else:
                try:
                    content = Path(f.file_path).read_text(encoding="utf-8")
                except Exception:
                    content = "无法读取文件内容"

                messages = [
                    {"role": "system", "content": "你是一位专业的检验科医师，请以JSON格式返回化验单分析结果。"},
                    {"role": "user", "content": f"{prompt}\n\n化验单内容：\n{content}"},
                ]
                data = await self.llm.chat_json(messages)

            results.append(LabFindings(
                source_file=f.original_name,
                abnormal_indicators=data.get("abnormal_indicators", []),
                summary=data.get("summary", ""),
            ))

        return results

    async def run_followup(
        self,
        instruction: str,
        existing_findings: list[LabFindings],
    ) -> str:
        """根据 LLM A 的指令，对已有化验结果做针对性补充分析。"""
        if not existing_findings:
            return "无可用的化验数据，无法执行补充分析。"

        context = "\n".join(
            f"[{f.source_file}] {f.summary}\n"
            f"异常指标：{json.dumps(f.abnormal_indicators, ensure_ascii=False)}"
            for f in existing_findings
        )

        messages = [
            {
                "role": "system",
                "content": (
                    "你是一位检验科医师。以下是之前对化验单的提取结果。"
                    "请根据主治医师的具体指令，做更深入的针对性分析。"
                ),
            },
            {
                "role": "user",
                "content": (
                    f"## 已有化验结果\n{context}\n\n"
                    f"## 主治医师指令\n{instruction}\n\n"
                    "请给出针对性的补充分析。"
                ),
            },
        ]
        return await self.llm.chat(messages)
