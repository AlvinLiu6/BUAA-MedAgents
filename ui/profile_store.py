"""
Persistent patient profile storage (JSON file).
"""
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

PROFILE_PATH = Path.home() / ".medagent" / "patient_profile.json"

_DEFAULTS: dict = {
    "gender": None,
    "age": None,
    "height": None,
    "weight": None,
    "allergy": "",
    "past_history": "",
}


def load_profile() -> dict:
    """Load profile from disk; return defaults if file missing or corrupt."""
    if PROFILE_PATH.exists():
        try:
            data = json.loads(PROFILE_PATH.read_text(encoding="utf-8"))
            return {**_DEFAULTS, **data}
        except Exception as e:
            logger.warning("Failed to load patient profile: %s", e)
    return dict(_DEFAULTS)


def save_profile(profile: dict) -> None:
    """Persist profile to disk."""
    try:
        PROFILE_PATH.parent.mkdir(parents=True, exist_ok=True)
        PROFILE_PATH.write_text(
            json.dumps(profile, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        logger.info("Patient profile saved to %s", PROFILE_PATH)
    except Exception as e:
        logger.error("Failed to save patient profile: %s", e)
