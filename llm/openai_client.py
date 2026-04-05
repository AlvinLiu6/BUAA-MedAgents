import base64
import json
import logging
from pathlib import Path

import httpx
from openai import AsyncOpenAI

from config import Settings

logger = logging.getLogger(__name__)


class LLMClient:
    def __init__(self, settings: Settings, *, use_vision_model: bool = False):
        if use_vision_model:
            api_key = settings.vision_api_key or settings.openai_api_key
            base_url = settings.vision_base_url
            self.model = settings.vision_model
        else:
            api_key = settings.openai_api_key
            base_url = settings.openai_base_url
            self.model = settings.openai_model

        self.client = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=httpx.Timeout(120.0, connect=30.0),  # 30s connect, 120s total
            max_retries=3,
        )

    async def chat(
        self,
        messages: list[dict],
        temperature: float = 0.3,
    ) -> str:
        logger.debug("LLM request: model=%s, messages=%d", self.model, len(messages))
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
        )
        content = response.choices[0].message.content or ""
        logger.debug("LLM response: %s...", content[:200])
        return content

    async def chat_json(
        self,
        messages: list[dict],
        temperature: float = 0.3,
    ) -> dict:
        logger.debug("LLM JSON request: model=%s", self.model)
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            response_format={"type": "json_object"},
        )
        content = response.choices[0].message.content or "{}"
        return json.loads(content)

    async def chat_with_image(
        self,
        system_prompt: str,
        user_text: str,
        image_path: str,
        temperature: float = 0.3,
    ) -> str:
        image_data = Path(image_path).read_bytes()
        b64 = base64.b64encode(image_data).decode()
        suffix = Path(image_path).suffix.lower().lstrip(".")
        media_type = {"jpg": "jpeg", "jpeg": "jpeg", "png": "png"}.get(suffix, "png")

        messages = [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": user_text},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/{media_type};base64,{b64}",
                        },
                    },
                ],
            },
        ]
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
        )
        return response.choices[0].message.content or ""

    async def chat_with_image_json(
        self,
        system_prompt: str,
        user_text: str,
        image_path: str,
        temperature: float = 0.3,
    ) -> dict:
        image_data = Path(image_path).read_bytes()
        b64 = base64.b64encode(image_data).decode()
        suffix = Path(image_path).suffix.lower().lstrip(".")
        media_type = {"jpg": "jpeg", "jpeg": "jpeg", "png": "png"}.get(suffix, "png")

        messages = [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": user_text},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/{media_type};base64,{b64}",
                        },
                    },
                ],
            },
        ]
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            response_format={"type": "json_object"},
        )
        content = response.choices[0].message.content or "{}"
        return json.loads(content)
