"""
The learning path: which concept comes first, and what unlocks what.

Beginners start from the basics (vectors) instead of being dropped into
density matrices. A concept unlocks when every prerequisite is mastered
(all 3 levels passed) - unlocking the next concept is the reward for
finishing the hardest level.

The agent recommends what to study next:
  1. a mastered concept whose spaced-repetition review is due (keep it fresh),
  2. otherwise the first unlocked concept on the path that is not mastered,
  3. otherwise (all mastered) the concept whose review comes up soonest.
"""

from datetime import date
from pathlib import Path

import profile_store

MATERIALS_DIR = Path(__file__).parent / "materials"

PATH = [
    {"id": "state_vector", "title": "Qubit state vectors",
     "material": "state_vector.txt", "prerequisites": []},
    {"id": "outer_product", "title": "Outer products |ψ⟩⟨φ|",
     "material": "outer_product.txt", "prerequisites": ["state_vector"]},
    {"id": "density_matrix", "title": "Pure-state density matrix",
     "material": "density_matrix.txt", "prerequisites": ["outer_product"]},
    {"id": "mixed_state", "title": "Mixed states and purity",
     "material": "mixed_state.txt", "prerequisites": ["density_matrix"]},
]
BY_ID = {step["id"]: step for step in PATH}


def material(concept_id: str) -> str:
    return (MATERIALS_DIR / BY_ID[concept_id]["material"]).read_text(encoding="utf-8")


def _record(profile: dict, concept_id: str) -> dict | None:
    return profile["concepts"].get(concept_id)


def is_mastered(profile: dict, concept_id: str) -> bool:
    # Uses the level, not the status: a wrong answer in a later review puts the
    # status back to "review", but the concept has still been mastered once.
    rec = _record(profile, concept_id)
    return bool(rec) and rec["level"] >= profile_store.MAX_LEVEL


def is_unlocked(profile: dict, concept_id: str) -> bool:
    return all(is_mastered(profile, p) for p in BY_ID[concept_id]["prerequisites"])


def review_due(profile: dict, concept_id: str, today: date | None = None) -> bool:
    rec = _record(profile, concept_id)
    today = today or date.today()
    return bool(rec and rec["next_review"]
                and date.fromisoformat(rec["next_review"]) <= today)


def status(profile: dict, concept_id: str, today: date | None = None) -> str:
    """locked | new | learning | review_due | mastered"""
    if not is_unlocked(profile, concept_id):
        return "locked"
    rec = _record(profile, concept_id)
    if not rec or not rec["history"]:
        return "new"
    if is_mastered(profile, concept_id):
        return "review_due" if review_due(profile, concept_id, today) else "mastered"
    return "learning"


def recommend(profile: dict, today: date | None = None) -> tuple[str, str]:
    """Return (concept_id, reason) for what to study next."""
    today = today or date.today()
    due = [s["id"] for s in PATH if status(profile, s["id"], today) == "review_due"]
    if due:
        oldest = min(due, key=lambda c: profile["concepts"][c]["next_review"])
        return oldest, "a spaced-repetition review is due - keep it fresh"
    for step in PATH:
        st = status(profile, step["id"], today)
        if st == "new":
            return step["id"], "next step on your path"
        if st == "learning":
            level = profile["concepts"][step["id"]]["level"]
            return step["id"], f"continue where you left off (level {level}/3 passed)"
    soonest = min(PATH, key=lambda s: profile["concepts"][s["id"]]["next_review"])
    return soonest["id"], "whole path mastered - this review comes up first"


def newly_unlocked(profile: dict, mastered_id: str) -> list[str]:
    """Concepts that list mastered_id as a prerequisite and are now open."""
    return [s["id"] for s in PATH
            if mastered_id in s["prerequisites"] and is_unlocked(profile, s["id"])]
