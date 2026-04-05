from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    openai_api_key: str = ""
    openai_model: str = "gpt-4o"
    openai_base_url: str = "https://api.openai.com/v1"

    # Vision model for non-xray image content extraction (e.g. Qwen-VL)
    # If vision_api_key is empty, falls back to openai_api_key
    vision_api_key: str = ""
    vision_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    vision_model: str = "qwen-vl-plus"

    xrayglm_mode: str = "mock"  # "mock" | "local"
    xrayglm_checkpoint_path: str = "./checkpoints/XrayGLM"
    xrayglm_prompt: str = "详细描述这张胸部X光片的诊断结果"

    max_review_rounds: int = 3
    log_level: str = "INFO"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}
