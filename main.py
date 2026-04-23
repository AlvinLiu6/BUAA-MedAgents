import logging
import os
import sys
import threading
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
from ui.app import create_ui, get_diagnosis_css
from ui.portal import create_portal, get_portal_css
from ui.profile_store import load_profile

# Ports
PORTAL_PORT = 7860
DIAGNOSIS_PORT = 7861



def main():
    settings = Settings()

    # Setup logging
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )

    logger = logging.getLogger("MedAgent")
    logger.info("Initializing BUAA-MedAgents...")
    logger.info("LLM Model: %s", settings.openai_model)
    logger.info("Vision Model: %s @ %s", settings.vision_model, settings.vision_base_url)
    logger.info("XrayGLM Mode: %s", settings.xrayglm_mode)
    logger.info("Max Review Rounds: %d", settings.max_review_rounds)

    # Load persistent patient profile from disk (shared between portal & diagnosis)
    patient_profile: dict = load_profile()
    logger.info("Patient profile loaded from disk: %s", patient_profile)

    # Build orchestrator (also exposes the main LLM for portal news)
    llm = LLMClient(settings)
    vision_llm = LLMClient(settings, use_vision_model=True)
    xrayglm = create_xrayglm(settings)

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

    # Build diagnosis UI (runs on a background thread, separate port)
    diagnosis_app = create_ui(orchestrator,
                              patient_profile=patient_profile,
                              portal_port=PORTAL_PORT)
    diagnosis_started = threading.Event()

    def _run_diagnosis():
        diagnosis_app.launch(
            server_name="127.0.0.1",
            server_port=DIAGNOSIS_PORT,
            prevent_thread_lock=True,
            quiet=True,
            css=get_diagnosis_css(),
        )
        diagnosis_started.set()

    diag_thread = threading.Thread(target=_run_diagnosis, daemon=True)
    diag_thread.start()
    diagnosis_started.wait(timeout=15)
    logger.info("Diagnosis system ready at http://127.0.0.1:%d", DIAGNOSIS_PORT)

    # Build and launch portal (main UI, foreground)
    portal = create_portal(
        diagnosis_port=DIAGNOSIS_PORT,
        patient_profile=patient_profile,
        llm=llm,
    )
    logger.info("Launching portal at http://127.0.0.1:%d", PORTAL_PORT)
    portal.launch(
        server_name="127.0.0.1",
        server_port=PORTAL_PORT,
        css=get_portal_css(),
    )


if __name__ == "__main__":
    main()
