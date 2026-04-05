import logging
import os
import sys
from pathlib import Path

# Ensure Gradio can connect to localhost (fixes 502 in proxy environments)
os.environ.setdefault("no_proxy", "localhost,127.0.0.1")

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from config import Settings
from llm import LLMClient
from xrayglm import create_xrayglm
from agents import (
    TriageAgent, ImageAgent, LabAgent,
    RecordAgent, DiagnosisAgent, ReviewAgent,
)
from orchestrator import PipelineOrchestrator
from ui.app import create_ui, CUSTOM_CSS


def main():
    settings = Settings()

    # Setup logging
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )

    logger = logging.getLogger("MedAgent")
    logger.info("Initializing MedAgent...")
    logger.info("LLM Model: %s", settings.openai_model)
    logger.info("XrayGLM Mode: %s", settings.xrayglm_mode)
    logger.info("Max Review Rounds: %d", settings.max_review_rounds)

    # Initialize components
    llm = LLMClient(settings)
    vision_llm = LLMClient(settings, use_vision_model=True)
    logger.info("Vision Model: %s @ %s", settings.vision_model, settings.vision_base_url)
    xrayglm = create_xrayglm(settings)

    # Build pipeline
    orchestrator = PipelineOrchestrator(
        triage=TriageAgent(llm),
        image_agent=ImageAgent(xrayglm, llm),
        lab_agent=LabAgent(llm, vision_llm=vision_llm),
        record_agent=RecordAgent(llm, vision_llm=vision_llm),
        diagnosis_agent=DiagnosisAgent(llm),
        review_agent=ReviewAgent(llm),
        llm=llm,
        vision_llm=vision_llm,
        max_rounds=settings.max_review_rounds,
    )

    # Launch UI
    app = create_ui(orchestrator)
    app.launch(
        server_name="127.0.0.1",
        server_port=7860,
        css=CUSTOM_CSS,
    )


if __name__ == "__main__":
    main()
