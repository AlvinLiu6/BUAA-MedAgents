from .interface import XrayGLMInterface
from .mock_model import MockXrayGLM

from config import Settings


def create_xrayglm(settings: Settings) -> XrayGLMInterface:
    if settings.xrayglm_mode == "local":
        from .local_model import LocalXrayGLM
        return LocalXrayGLM(settings.xrayglm_checkpoint_path, settings.xrayglm_prompt)
    return MockXrayGLM()


__all__ = ["XrayGLMInterface", "MockXrayGLM", "create_xrayglm"]
