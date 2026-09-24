"""
Tutor logic: generate a question at a given difficulty, grade the
learner's answer, and write a short review page when they get stuck.
"""

from llm import ask, ask_json

DIFFICULTY_NAMES = {1: "recall", 2: "apply", 3: "transfer"}

DIFFICULTY_RULES = {
    1: "RECALL: ask for a key definition or fact that appears in the material.",
    2: ("APPLY: ask the learner to work out a small concrete example or "
        "calculation (use numbers, vectors or matrices if the topic allows)."),
    3: ("TRANSFER: ask the learner to apply the idea to a situation that is "
        "NOT described in the material."),
}


def generate_question(material: str, concept: str, difficulty: int,
                      weak_points: list[str]) -> dict:
    """Return {"question", "expected_answer", "key_points"}."""
    focus = ""
    if weak_points:
        focus = ("The learner previously struggled with: "
                 + "; ".join(weak_points[-3:])
                 + ". If relevant, target that gap.")

    prompt = f"""You are a patient quantum computing tutor for an undergraduate
electrical engineering student. The current concept is "{concept}".

Write exactly ONE question. Difficulty level {difficulty}/3 -
{DIFFICULTY_RULES[difficulty]}
{focus}
The question must be answerable in a few sentences or a short calculation.

Return JSON with these keys:
- "question": the question text
- "expected_answer": a correct model answer, including a brief worked solution
- "key_points": a list of 1-3 points a correct answer MUST contain

Study material:
\"\"\"
{material}
\"\"\"
"""
    return ask_json(prompt, temperature=0.7)


def grade_answer(question: dict, answer: str) -> dict:
    """Return {"correct": bool, "feedback": str, "weak_point": str | None}."""
    prompt = f"""You are grading a student's answer. Be fair but strict:
the answer is correct only if it covers every key point, even if the
wording is different. Minor notation slips are fine; conceptual errors are not.

Question: {question["question"]}
Model answer: {question["expected_answer"]}
Key points: {question["key_points"]}

Student answer: \"\"\"{answer}\"\"\"

Return JSON with these keys:
- "correct": true or false
- "feedback": 2-3 sentences to the student - what was right, what was missing
- "weak_point": if incorrect, a short phrase naming the exact gap
  (e.g. "purity test tr(rho^2)"); if correct, null
"""
    result = ask_json(prompt, temperature=0.0)
    result["correct"] = bool(result.get("correct"))
    return result


def review_page(material: str, concept: str, weak_point: str) -> str:
    """A short focused explanation to read before trying again."""
    prompt = f"""A student studying "{concept}" got stuck on: {weak_point}.

Write a short review page (max 200 words) that:
1. Explains that specific point in plain language
2. Gives one small worked example
3. Ends with one tip for remembering it

Base it on this material where possible:
\"\"\"
{material}
\"\"\"
"""
    return ask(prompt)
