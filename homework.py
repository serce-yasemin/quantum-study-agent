"""
Homework: built at the end of every session and saved in the learner profile.

Flow:  checked book list + live web search (Tavily, trusted sites) + our own
link check  ->  the model picks from those lists and writes the task and two
check questions  ->  the assignment is stored under profile["assignments"].

Checking it later:  2 questions.  2/2 -> done.  1 wrong -> one extra question
on that gap (right -> done, wrong -> short review page, stays open).
2 wrong -> review page straight away, stays open.
"""

from datetime import date

import curriculum
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


def _material(assignment: dict) -> str:
    """Study text for this homework: the path material, or - for a learner's
    own topic - what the check questions themselves say."""
    if assignment["concept"] in curriculum.BY_ID:
        return curriculum.material(assignment["concept"])
    return "\n".join(f"{q['question']}\n{q['expected_answer']}"
                     for q in assignment["check_questions"])


def _title(assignment: dict) -> str:
    step = curriculum.BY_ID.get(assignment["concept"])
    return step["title"] if step else assignment["concept"]


def _grade(question: dict, answer: str) -> dict:
    graded = tutor.grade_answer({"question": question["question"],
                                 "expected_answer": question["expected_answer"],
                                 "key_points": []}, answer)
    return {"question": question["question"], "answer": answer,
            "expected_answer": question["expected_answer"], **graded}


def _review(assignment: dict, result: dict) -> str:
    return tutor.review_page(_material(assignment), _title(assignment),
                             result.get("weak_point") or "the idea behind this question",
                             {"question": result["question"],
                              "expected_answer": result["expected_answer"]},
                             result["answer"])


def _finish(assignment: dict) -> None:
    assignment["status"] = "done"
    assignment["done_on"] = date.today().isoformat()


def check(assignment: dict, answers: list[str]) -> dict:
    """Grade the learner's answers to the two check questions.

    - both correct      -> the homework is done
    - one wrong         -> one extra question on that gap (see check_extra)
    - both wrong        -> no extra question: a short review page per gap,
                           the homework stays open
    Every attempt is logged in assignment["checks"].

    Returns {"results": [...], "extra": question | None, "reviews": [str]}.
    """
    results = [_grade(q, a) for q, a in zip(assignment["check_questions"], answers)]
    missed = [r for r in results if not r["correct"]]
    assignment.setdefault("checks", []).append({
        "date": date.today().isoformat(),
        "correct": [r["correct"] for r in results],
        "gaps": [r.get("weak_point") for r in missed],
    })
    extra, reviews = None, []
    if results and not missed:
        _finish(assignment)
    elif len(missed) == 1:
        m = missed[0]
        extra = tutor.gap_question(_material(assignment), _title(assignment),
                                   m, m["answer"], m.get("weak_point"))
        extra["gap"] = m.get("weak_point")
    else:
        reviews = [_review(assignment, m) for m in missed]
        assignment["checks"][-1]["review_shown"] = True
    return {"results": results, "extra": extra, "reviews": reviews}


def check_extra(assignment: dict, extra: dict, answer: str) -> dict:
    """Grade the extra question asked after exactly one miss.

    Correct -> it was a slip: the homework is done.
    Wrong   -> a real gap: show a short review page, the homework stays open.

    Returns {"result": {...}, "review": str | None}.
    """
    result = _grade(extra, answer)
    if not result["correct"] and not result.get("weak_point"):
        result["weak_point"] = extra.get("gap")
    log = assignment["checks"][-1]
    log["extra_correct"] = result["correct"]
    review = None
    if result["correct"]:
        _finish(assignment)
    else:
        log["gaps"].append(result.get("weak_point"))
        log["review_shown"] = True
        review = _review(assignment, result)
    return {"result": result, "review": review}
