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
                      weak_points: list[str],
                      previous_questions: list[str] | None = None) -> dict:
    """Return {"question", "expected_answer", "key_points"}."""
    focus = ""
    if weak_points:
        focus = ("The learner previously struggled with: "
                 + "; ".join(weak_points[-3:])
                 + ". If relevant, target that gap.")
    if previous_questions:
        focus += ("\nAlready asked this session - do NOT repeat or closely "
                  "paraphrase these; test the idea from a different angle "
                  "or with different numbers:\n- "
                  + "\n- ".join(previous_questions[-5:]))

    prompt = f"""You are a patient quantum computing tutor for an undergraduate
electrical engineering student. The current concept is "{concept}".

Write exactly ONE question. Difficulty level {difficulty}/3 -
{DIFFICULTY_RULES[difficulty]}
{focus}
The question must be answerable in a few sentences or a short calculation.

Return JSON with these keys:
- "question": the question text
- "expected_answer": a correct model answer, including a brief worked solution
- "key_points": a list of 1-3 points a correct answer MUST contain. Include
  ONLY what the question explicitly asks for - never extra facts that the
  question does not request.

Formatting: plain text only. No LaTeX, no HTML tags, no Markdown. Use Unicode
symbols instead (ρ, ψ, ⟨ ⟩, |0⟩, ², √, †).

Study material:
\"\"\"
{material}
\"\"\"
"""
    return ask_json(prompt, temperature=0.7)


def grade_answer(question: dict, answer: str) -> dict:
    """Return {"correct": bool, "feedback": str, "weak_point": str | None}."""
    prompt = f"""You are grading a student's answer. Judge it ONLY against
what the question actually asks.
- Mark it correct if it answers the question correctly, even with different
  wording or less detail than the model answer.
- Do NOT penalize the student for leaving out facts the question did not ask
  for. You may mention such extras in the feedback as a tip, but they must not
  change the verdict.
- Mark it incorrect only for a conceptual error, a wrong result, or a missing
  part that the question explicitly requested.

Question: {question["question"]}
Model answer: {question["expected_answer"]}
Key points: {question["key_points"]}

Student answer: \"\"\"{answer}\"\"\"

Return JSON with these keys:
- "correct": true or false
- "feedback": 2-3 sentences to the student - what was right, what was missing
- "weak_point": if incorrect, a short phrase naming the exact gap
  (e.g. "purity test tr(rho^2)"); if correct, null

Formatting: plain text only, no LaTeX, no HTML, no Markdown.
"""
    result = ask_json(prompt, temperature=0.0)
    result["correct"] = bool(result.get("correct"))
    return result


def review_page(material: str, concept: str, weak_point: str,
                question: dict, answer: str) -> str:
    """A short focused explanation to read before trying again.

    It sees the exact question the student missed and their answer, so the
    review targets that gap instead of a generic summary of the concept.
    """
    prompt = f"""A student studying "{concept}" just got this question wrong.

Question: {question["question"]}
Correct solution: {question["expected_answer"]}
Student's answer: \"\"\"{answer}\"\"\"
Identified gap: {weak_point}

Write a short review page (max 200 words) that:
1. Names the specific idea or technique the student was missing for THIS
   question (if they wrote "I don't know", teach the method from scratch)
2. Works through ONE similar example of the SAME type as the question, step by
   step, with different numbers - do NOT solve the original question itself,
   because the student will get a new question of this type next
3. Ends with one tip for remembering it

Formatting: this is shown in a terminal, so use plain text only. No LaTeX,
no HTML, no Markdown headings or bold. Use Unicode symbols (ρ, ψ, ⟨ ⟩, ², √).
Write matrices on separate lines, e.g.  ρ = [[a, b], [c, d]].

Base it on this material where possible:
\"\"\"
{material}
\"\"\"
"""
    return ask(prompt)
