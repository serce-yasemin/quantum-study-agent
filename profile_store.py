"""
The learner profile: the agent's long-term memory.

Stored as a local JSON file so the learner's data stays on their own
machine (it is listed in .gitignore and never pushed to GitHub).
"""

import json
from datetime import date, timedelta
from pathlib import Path

PROFILE_PATH = Path("learner_profile.json")

MAX_LEVEL = 3  # 1 = recall, 2 = apply, 3 = transfer

# Spaced repetition: how many days until the concept is asked again.
REVIEW_AFTER_DAYS = {
    "wrong": 1,
    "learning": 2,
    "mastered": 3,
}


def load() -> dict:
    if PROFILE_PATH.exists():
        return json.loads(PROFILE_PATH.read_text(encoding="utf-8"))
    return {"learner": {"goal": "", "interests": []}, "concepts": {}, "assignments": []}


def save(profile: dict) -> None:
    PROFILE_PATH.write_text(json.dumps(profile, indent=2, ensure_ascii=False),
                            encoding="utf-8")


def get_concept(profile: dict, name: str) -> dict:
    """Return the concept record, creating an empty one the first time."""
    return profile["concepts"].setdefault(name, {
        "prerequisites": [],
        "status": "learning",   # locked | learning | review | mastered
        "level": 0,             # highest difficulty passed (0-3)
        "history": [],
        "next_review": None,
    })


def record_attempt(concept: dict, difficulty: int, correct: bool,
                   weak_point: str | None) -> None:
    """Log one answer and move the concept up (or not) the difficulty ladder."""
    today = date.today()
    concept["history"].append({
        "date": today.isoformat(),
        "difficulty": difficulty,
        "correct": correct,
        "weak_point": weak_point,
    })

    if correct:
        concept["level"] = max(concept["level"], difficulty)
        if concept["level"] >= MAX_LEVEL:
            concept["status"] = "mastered"
            days = REVIEW_AFTER_DAYS["mastered"]
        else:
            concept["status"] = "learning"
            days = REVIEW_AFTER_DAYS["learning"]
    else:
        concept["status"] = "review"
        days = REVIEW_AFTER_DAYS["wrong"]

    concept["next_review"] = (today + timedelta(days=days)).isoformat()
