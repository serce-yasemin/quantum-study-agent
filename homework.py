"""
Homework: built at the end of every session and saved in the learner profile.

Flow:  checked book list + live web search (Tavily, trusted sites) + our own
link check  ->  the model picks from those lists and writes the task and two
check questions  ->  the assignment is stored under profile["assignments"].
"""

from datetime import date

import resources
import tutor


def create(profile: dict, concept: str, title: str, material: str,
           weak_point: str | None) -> dict:
    books = resources.book_options(concept)
    web_status = "ok"
    try:
        links = resources.find_web_resources(title, weak_point)
        if not resources.tavily_available():
            web_status = "no Tavily key - book only"
    except Exception as exc:          # search is a bonus; never block homework
        links, web_status = [], f"web search failed: {exc}"

    picked = tutor.make_assignment(material, title, weak_point, books, links)
    record = {
        "id": len(profile.setdefault("assignments", [])) + 1,
        "concept": concept,
        "created": date.today().isoformat(),
        "weak_point": weak_point,
        "book": books[picked["book"]] if picked["book"] is not None else None,
        "links": [links[i] for i in picked["links"]],
        "task": picked["task"],
        "check_questions": picked["check_questions"],
        "status": "open",            # open -> done (after the check questions)
        "web_search": web_status,
    }
    profile["assignments"].append(record)
    return record


def open_assignments(profile: dict) -> list[dict]:
    return [a for a in profile.get("assignments", []) if a["status"] == "open"]
