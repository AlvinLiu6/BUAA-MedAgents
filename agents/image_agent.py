import logging

from .base import BaseAgent
from llm import LLMClient
from models import UploadedFile, XrayFindings
from xrayglm.interface import XrayGLMInterface

logger = logging.getLogger(__name__)


class ImageAgent(BaseAgent):
    def __init__(self, xrayglm: XrayGLMInterface, llm: LLMClient | None = None):
        super().__init__("ImageAgent")
        self.xrayglm = xrayglm
        self.llm = llm

    async def run(self, xray_files: list[UploadedFile]) -> list[XrayFindings]:
        results = []
        for f in xray_files:
            logger.info("Analyzing X-ray: %s", f.original_name)
            raw_text = await self.xrayglm.analyze(f.file_path)

            abnormalities = []
            _NEGATIVE_PREFIXES = (
                "未见", "未发现", "无明显", "无", "不伴", "不存在",
                "未及", "未累及", "排除", "未提示", "无显著",
            )
            _ABNORMAL_KW = [
                "异常", "增粗", "模糊影", "增大", "积液", "结节",
                "肿块", "钙化", "骨折", "狭窄", "增宽", "炎症",
            ]
            for line in raw_text.split("\n"):
                line = line.strip()
                if not line:
                    continue
                for kw in _ABNORMAL_KW:
                    idx = line.find(kw)
                    if idx == -1:
                        continue
                    # 取关键词前面的片段，检查是否包含否定词
                    prefix = line[:idx]
                    if any(neg in prefix for neg in _NEGATIVE_PREFIXES):
                        continue
                    abnormalities.append(line)
                    break

            results.append(XrayFindings(
                image_path=f.file_path,
                findings=raw_text,
                abnormalities=abnormalities,
            ))

        return results

    async def run_followup(
        self,
        instruction: str,
        existing_findings: list[XrayFindings],
    ) -> str:
        """根据 LLM A 的指令，对已有影像做针对性补充分析。"""
        if not existing_findings:
            return "无可用的影像数据，无法执行补充分析。"

        # 如果有 LLM（GPT-4o vision），用它做针对性分析
        if self.llm:
            context = "\n".join(f.findings for f in existing_findings)
            messages = [
                {
                    "role": "system",
                    "content": (
                        "你是一位放射科医师。以下是之前对 X 光片的初步分析结果。"
                        "请根据主治医师的具体指令，对影像做更深入的针对性分析。"
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"## 初步影像分析结果\n{context}\n\n"
                        f"## 主治医师指令\n{instruction}\n\n"
                        "请给出针对性的补充分析。"
                    ),
                },
            ]
            return await self.llm.chat(messages)

        # 没有 LLM，返回已有结果摘要
        return "影像补充分析：" + " | ".join(
            f.findings[:200] for f in existing_findings
        )
