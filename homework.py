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


def check(assignment: dict, answers: list[str]) -> list[dict]:
    """Grade the learner's answers to the assignment's check questions.

    Both correct -> the homework counts as done. Otherwise it stays open so
    the learner can look again and retry later. Every attempt is logged.
    """
    results = []
    for q, answer in zip(assignment["check_questions"], answers):
        graded = tutor.grade_answer({"question": q["question"],
                                     "expected_answer": q["expected_answer"],
                                     "key_points": []}, answer)
        results.append({"question": q["question"], "answer": answer, **graded})

    passed = bool(results) and all(r["correct"] for r in results)
    assignment.setdefault("checks", []).append({
        "date": date.today().isoformat(),
        "correct": [r["correct"] for r in results],
        "gaps": [r.get("weak_point") for r in results if not r["correct"]],
    })
    if passed:
        assignment["status"] = "done"
        assignment["done_on"] = date.today().isoformat()
    return results
