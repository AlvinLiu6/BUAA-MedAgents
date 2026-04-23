"""
Health data storage: exercise plan, exercise check-ins, sleep records, nutrition plan.
"""
import json
import logging
import uuid
from datetime import date
from pathlib import Path

logger = logging.getLogger(__name__)

HEALTH_PATH = Path.home() / ".medagent" / "health_data.json"

_DEFAULTS: dict = {
    "exercise_plan": None,
    "exercise_checkins": {},
    "sleep_records": {},
    "nutrition_plan": None,
    "mood_records": {},    # {"YYYY-MM-DD": {"mood": int 1-5, "note": str}}
    "medications": [],     # [{"id": str, "name": str, "dosage": str, "frequency": str, "times": list}]
    "med_checkins": {},    # {"YYYY-MM-DD": [med_id, ...]}  — IDs taken today
    "medical_records": [], # [{"id": str, "date": str, "symptom": str, "diagnosis": str,
                           #   "treatment": str, "hospital": str, "note": str, "source": str}]
    "chronic_diseases": [],  # [{"id": str, "name": str, "diagnosed_date": str,
                             #   "medications": [{"med_id": str, "name": str, "dosage": str, "frequency": str}],
                             #   "indicators": [{"name": str, "target": str, "frequency": str}],
                             #   "note": str}]
}


def load_health() -> dict:
    if HEALTH_PATH.exists():
        try:
            data = json.loads(HEALTH_PATH.read_text(encoding="utf-8"))
            return {**_DEFAULTS, **data}
        except Exception as e:
            logger.warning("Failed to load health data: %s", e)
    return dict(_DEFAULTS)


def save_health(data: dict) -> None:
    try:
        HEALTH_PATH.parent.mkdir(parents=True, exist_ok=True)
        HEALTH_PATH.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except Exception as e:
        logger.error("Failed to save health data: %s", e)


def today_str() -> str:
    return date.today().isoformat()


def is_checked_in_today(health: dict) -> bool:
    return today_str() in health.get("exercise_checkins", {})


def get_unchecked_meds_today(health: dict) -> list:
    """Return medication names not yet taken today."""
    meds = [m["name"] for m in health.get("medications", [])]
    taken = set(health.get("med_checkins", {}).get(today_str(), []))
    return [m for m in meds if m not in taken]


def add_medication(health: dict, name: str, dosage: str, frequency: str, times: list) -> dict:
    med = {"id": str(uuid.uuid4())[:8], "name": name, "dosage": dosage,
           "frequency": frequency, "times": times}
    health.setdefault("medications", []).append(med)
    return med


def remove_medication(health: dict, med_id: str) -> None:
    health["medications"] = [m for m in health.get("medications", []) if m["id"] != med_id]


def get_unchecked_med_names(health: dict) -> list[str]:
    """Return names of medications not yet taken today."""
    meds = health.get("medications", [])
    today = today_str()
    taken_ids = set(health.get("med_checkins", {}).get(today, []))
    return [m["name"] for m in meds if m["id"] not in taken_ids]


# ── Medical records ──

def add_medical_record(health: dict, *, record_date: str, symptom: str,
                       diagnosis: str = "", treatment: str = "",
                       hospital: str = "", note: str = "",
                       source: str = "manual") -> dict:
    rec = {
        "id": str(uuid.uuid4())[:8],
        "date": record_date,
        "symptom": symptom,
        "diagnosis": diagnosis,
        "treatment": treatment,
        "hospital": hospital,
        "note": note,
        "source": source,
    }
    health.setdefault("medical_records", []).append(rec)
    return rec


def update_medical_record(health: dict, rec_id: str, **fields) -> None:
    for rec in health.get("medical_records", []):
        if rec["id"] == rec_id:
            rec.update(fields)
            return


def remove_medical_record(health: dict, rec_id: str) -> None:
    health["medical_records"] = [
        r for r in health.get("medical_records", []) if r["id"] != rec_id
    ]


# ── Chronic diseases ──

def add_chronic_disease(health: dict, *, name: str, diagnosed_date: str = "",
                        medications: list | None = None,
                        indicators: list | None = None,
                        note: str = "") -> dict:
    cd = {
        "id": str(uuid.uuid4())[:8],
        "name": name,
        "diagnosed_date": diagnosed_date,
        "medications": medications or [],
        "indicators": indicators or [],
        "note": note,
    }
    health.setdefault("chronic_diseases", []).append(cd)
    return cd


def update_chronic_disease(health: dict, cd_id: str, **fields) -> None:
    for cd in health.get("chronic_diseases", []):
        if cd["id"] == cd_id:
            cd.update(fields)
            return


def remove_chronic_disease(health: dict, cd_id: str) -> None:
    health["chronic_diseases"] = [
        c for c in health.get("chronic_diseases", []) if c["id"] != cd_id
    ]


def sync_chronic_meds_to_medications(health: dict) -> None:
    """Sync medications from chronic diseases into the global medications list.

    For each med in chronic_diseases, if no medication with the same name+dosage
    exists in health["medications"], add it. Adds a 'chronic_id' field so we
    know the source.
    """
    existing = {(m["name"], m.get("dosage", "")) for m in health.get("medications", [])}
    for cd in health.get("chronic_diseases", []):
        for cm in cd.get("medications", []):
            key = (cm["name"], cm.get("dosage", ""))
            if key not in existing:
                med = {
                    "id": str(uuid.uuid4())[:8],
                    "name": cm["name"],
                    "dosage": cm.get("dosage", ""),
                    "frequency": cm.get("frequency", ""),
                    "times": [],
                    "chronic_id": cd["id"],
                }
                health.setdefault("medications", []).append(med)
                existing.add(key)
