from typing import Protocol


class XrayGLMInterface(Protocol):
    async def analyze(self, image_path: str) -> str:
        ...
