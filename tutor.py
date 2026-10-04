"""
Tutor logic: generate a question at a given difficulty, grade the
learner's answer, and write a short review page when they get stuck.
"""

import random

from llm import ask, ask_json

# Physics conventions every prompt must follow, so lessons, questions, grading
# and review pages never contradict each other (e.g. the sign of a phase).
CONVENTIONS = """Conventions (follow exactly):
- Write qubit states as |ψ⟩ = a|0⟩ + b·e^(iφ)|1⟩ with a, b ≥ 0.
- Then ρ = |ψ⟩⟨ψ| has ρ₀₁ = ⟨0|ρ|1⟩ = a·b·e^(−iφ) and ρ₁₀ = a·b·e^(+iφ).
- "Relative phase" means φ, the phase of |1⟩ relative to |0⟩: φ = arg(ρ₁₀) = −arg(ρ₀₁).
- The coherence magnitude is |ρ₀₁| = |ρ₁₀|."""

DIFFICULTY_NAMES = {1: "recall", 2: "apply", 3: "transfer"}

DIFFICULTY_RULES = {
    1: "RECALL: ask for a key definition or fact that appears in the material.",
    2: ("APPLY: ask the learner to work out a small concrete example or "
        "calculation (use numbers, vectors or matrices if the topic allows)."),
    3: ("TRANSFER: ask the learner to apply the idea to a situation that is "
        "NOT described in the material. The situation must be new, but the "
        "tools must not: solving it may only need ideas from the material plus "
        "basic linear algebra. Never require a technique the material does not "
        "teach (e.g. partial trace, a specific gate, entanglement measures) - "
        "that tests a different concept, not transfer of this one."),
}


def learning_objective(material: str, concept: str, difficulty: int) -> str:
    """One sentence: the single skill this level teaches AND tests.

    The lesson card and every question at this level are built from the same
    objective, so the learner is never asked about something the lesson did
    not teach (constructive alignment).
    """
    prompt = f"""You are planning one short study step on "{concept}" for a beginner.
Difficulty level {difficulty}/3 - {DIFFICULTY_RULES[difficulty]}

Write ONE learning objective: a single sentence starting with "The learner can ...".
- It must be teachable in about 120 words with one tiny example.
- It may only use ideas that appear in the study material (plus basic linear
  algebra). Do NOT introduce observables, measurements in other bases, gates,
  partial traces or anything else the material does not cover.

Plain text only: no LaTeX. Write powers as |a|² and phases as e^(iφ).

Reply with the sentence only.

Study material:
\"\"\"
{material}
\"\"\"
"""
    return ask(prompt, temperature=0.2).strip().splitlines()[0]


def generate_question(material: str, concept: str, difficulty: int,
                      weak_points: list[str],
                      previous_questions: list[str] | None = None,
                      objective: str | None = None) -> dict:
    """Return {"question", "expected_answer", "key_points", "hint"}."""
    focus = ""
    if objective:
        focus = (f"The question MUST test exactly this learning objective, "
                 f"which the learner was just taught: {objective}\n"
                 "Do not require any idea beyond it.\n")
    if weak_points:
        focus += ("The learner previously struggled with: "
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
- "hint": one short nudge toward the method, WITHOUT giving the answer

{CONVENTIONS}

Formatting: plain text only. No LaTeX, no HTML tags, no Markdown. Use Unicode
symbols instead (ρ, ψ, ⟨ ⟩, |0⟩, ², √, †). Write powers as |a|² (not |a|^2)
and phases as e^(iφ) (never braces like e^{{iφ}}). Subscripts: ρ₀₀, ρ₁₁.

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

The student types on a plain keyboard. Treat these spellings as the symbols
they stand for and never mark an answer down for them: psi, phi, theta, rho,
pi; sqrt(2) or 1/sqrt2; |0> and <phi|psi> for kets and bras; ^2 for a square;
* for multiplication; conj or * after a number for a complex conjugate.
If the question has parts (a), (b), (c), the answer is given part by part;
every part the question asks for must be right.

Return JSON with these keys:
- "correct": true or false
- "feedback": 2-3 sentences to the student - what was right, what was missing
- "weak_point": if incorrect, a short phrase naming the exact gap
  (e.g. "purity test tr(rho^2)"); if correct, null

{CONVENTIONS}

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

{CONVENTIONS}

Formatting: this is shown in a terminal, so use plain text only. No LaTeX,
no HTML, no Markdown headings or bold. Use Unicode symbols (ρ, ψ, ⟨ ⟩, ², √).
Write matrices on separate lines, e.g.  ρ = [[a, b], [c, d]].

Base it on this material where possible:
\"\"\"
{material}
\"\"\"
"""
    return ask(prompt)


def micro_lesson(material: str, concept: str, difficulty: int,
                 objective: str) -> str:
    """A short 'teach first' card shown before the questions of a level.

    Assumes the learner has NOT read the material yet: explain first, then ask.
    Inspired by micro-learning apps that teach one idea per ~3-minute step.
    Teaches exactly the objective the questions will test.
    """
    prompt = f"""Teach a beginner the concept "{concept}".
Teach exactly this objective and nothing beyond it: {objective}
Assume they have NOT read the study material and know only basic linear algebra.

Rules:
- Max 120 words. One idea only. Short sentences, no filler phrases.
- Build from something they already know (vectors, matrices) to the new idea.
- Include ONE tiny worked example with small numbers.
- Draw every vector or matrix as a small text grid, e.g.

      ρ = | 0.5  0.5 |
          | 0.5  0.5 |

- Plain text only: no LaTeX, no HTML, no Markdown. Unicode symbols are fine.

{CONVENTIONS}

Study material (use it as the source of truth):
\"\"\"
{material}
\"\"\"
"""
    return ask(prompt)


def simulate_answer(question: dict, persona: str) -> str:
    """Answer as a simulated student - lets the developer test the full loop
    without typing answers by hand.

    persona: "strong" (answers correctly), "weak" (makes a typical mistake).
    """
    if persona == "strong":
        instruction = ("Answer correctly and briefly, like a good student. "
                       "Do not copy the model answer word for word.")
    else:
        instruction = ("Answer like a beginner who makes ONE typical, realistic "
                       "mistake for this topic (e.g. forgets a normalisation "
                       "factor or mixes up a sign). Keep it short.")
    prompt = f"""You are role-playing a student in a quantum computing course.
{instruction}

Question: {question["question"]}
(For reference only - correct solution: {question["expected_answer"]})

Write only the student's answer, in plain text."""
    return ask(prompt, temperature=0.8)


def make_assignment(material: str, concept: str, weak_point: str | None,
                    books: list[dict], links: list[dict]) -> dict:
    """Homework for after the session.

    The model never writes a reference itself: it only PICKS a book section
    and web links by number from lists our code built (a checked book list,
    and links our code opened). Returns
    {"book": int | None, "links": [int], "task": str,
     "check_questions": [{"question", "expected_answer"}]}.
    The check questions are saved now and asked when the learner says the
    homework is done.
    """
    book_list = "\n".join(f"{i}. {b['section']} (pp. {b['pages']}) - {b['focus']}"
                          for i, b in enumerate(books)) or "(none)"
    link_list = "\n".join(f"{i}. {l['title']} - {l['url']}\n   {l['snippet']}"
                          for i, l in enumerate(links)) or "(none)"
    gap = (f'In today\'s session the learner struggled with: "{weak_point}".'
           if weak_point else "The learner made no mistakes today - deepen the topic.")

    prompt = f"""You are a quantum computing tutor setting short homework on "{concept}".
{gap}

Pick resources ONLY from these numbered lists. Never invent a book, section,
page or URL.

Book sections:
{book_list}

Web resources (already checked - they exist and load):
{link_list}

Return JSON only:
- "book": the number of the best book section, or null if the list is empty
- "links": a list of 0-2 numbers of the most useful web resources
- "task": 2-3 sentences telling the learner exactly what to read or watch and
  what to pay attention to (tie it to today's gap if there is one). About
  20-30 minutes of work. Refer to the book section and videos/pages by their
  title - never by list number (the learner does not see the numbers).
- "check_questions": exactly 2 objects {{"question", "expected_answer"}} that
  someone who did the homework can answer in 1-3 lines. They must be answerable
  from the study material below plus the homework - no new techniques.

Stay inside the study material: the task and the check questions may only use
ideas that appear in it. Do not bring in later topics (for example, do not
mention density matrices or ρ₀₁ unless the material itself covers them), and
apply a convention below only if the material covers that idea.

{CONVENTIONS}

Formatting: plain text only. No LaTeX, no Markdown. Use Unicode symbols
(ρ, ψ, ⟨ ⟩, ², √).

Study material:
\"\"\"
{material}
\"\"\"
"""
    raw = ask_json(prompt, temperature=0.3)

    # Keep only choices that point into our lists - drop anything else.
    book = raw.get("book")
    book = book if isinstance(book, int) and 0 <= book < len(books) else (0 if books else None)
    chosen = [i for i in raw.get("links") or [] if isinstance(i, int) and 0 <= i < len(links)]
    checks = [q for q in raw.get("check_questions") or []
              if isinstance(q, dict) and q.get("question") and q.get("expected_answer")]
    return {"book": book, "links": list(dict.fromkeys(chosen))[:2],
            "task": str(raw.get("task") or "").strip(),
            "check_questions": checks[:2]}


def gap_question(material: str, concept: str, missed_question: dict,
                 student_answer: str, gap: str | None) -> dict:
    """One more check question after a miss in the homework check.

    It tests the SAME gap from a different angle, so we can tell a slip
    from a real misunderstanding. Returns {"question", "expected_answer"}.
    """
    prompt = f"""A student did homework on "{concept}" and then missed this check question.

Question: {missed_question["question"]}
Correct answer: {missed_question["expected_answer"]}
Student's answer: \"\"\"{student_answer}\"\"\"
Identified gap: {gap or "unknown"}

Write ONE new short question that tests the SAME idea from a different angle
or with different numbers. Someone who understands the idea can answer it in
1-3 lines. Do not repeat the original question. No new techniques.

Return JSON with these keys:
- "question": the question text
- "expected_answer": a correct model answer in 1-3 lines

{CONVENTIONS}

Formatting: plain text only. No LaTeX, no Markdown. Use Unicode symbols
(ρ, ψ, ⟨ ⟩, ², √).

Study material:
\"\"\"
{material}
\"\"\"
"""
    raw = ask_json(prompt, temperature=0.5)
    return {"question": str(raw.get("question") or "").strip(),
            "expected_answer": str(raw.get("expected_answer") or "").strip()}


def lesson_plan(material: str, concept: str, difficulty: int,
                figures: dict | None = None) -> dict | None:
    """Objective + lesson cards in ONE model call (starting a lesson used to
    take two calls, one after the other). Returns {"objective", "cards"} or
    None if the reply does not have the right shape."""
    cards = lesson_cards(material, concept, difficulty, None, figures)
    if not cards or not cards.get("objective"):
        return None
    return {"objective": cards.pop("objective"), "figure": cards.pop("figure", None),
            "figure_numbers": cards.pop("figure_numbers", None), "cards": cards}


def lesson_cards(material: str, concept: str, difficulty: int,
                 objective: str | None, figures: dict | None = None) -> dict | None:
    """A lesson in four small cards instead of one block of text.

    1. bridge   - start from something the learner already knows
    2. idea     - the one new idea (the app shows a figure next to it)
    3. example  - a worked example, ONE operation per step, each with its reason
    4. try_it   - a multiple-choice warm-up; not graded, costs nothing

    The model writes the cards; our code checks their shape and shuffles the
    answer options (models tend to put the right answer first). Returns None
    if the reply does not have the right shape - the caller then falls back
    to the plain one-card lesson.
    """
    if objective:
        goal = f"Teach exactly this objective and nothing beyond it: {objective}"
        goal_key = ""
    else:           # one call instead of two: the model also writes the objective
        goal = (f"Difficulty level {difficulty}/3 - {DIFFICULTY_RULES[difficulty]}\n"
                "First choose ONE learning objective for this level, then teach "
                "exactly that objective and nothing beyond it.")
        goal_key = ('- "objective": ONE sentence starting with "The learner can ...". '
                    "It may only use ideas that appear in the study material (plus "
                    "basic linear algebra) and must be teachable with one tiny "
                    "example.\n")
    if figures:
        # The model never draws: it only picks one of our own pictures by key.
        listing = "\n".join(f'  "{key}": {what}' for key, what in figures.items())
        figure_key = ('- "figure": the key of the ONE picture from this list that '
                      "shows exactly the idea you teach, or \"none\" if no picture "
                      "fits (a wrong picture is worse than none):\n" + listing + "\n"
                      '- "figure_numbers": the plain real numbers your worked '
                      "example starts from, as a list, so the picture can start "
                      "from the same numbers - for \"outer_table\": [column top, "
                      "column bottom, row left, row right]; for \"normalize\": "
                      "[first entry, second entry]; otherwise [].\n")
    else:
        figure_key = ""
    prompt = f"""Teach a beginner the concept "{concept}" in four small cards.
{goal}
Assume they have NOT read the study material and know only basic linear algebra
(vectors, matrices, complex numbers).

Return JSON with these keys:
{goal_key}{figure_key}- "bridge": at most 2 short sentences (max 30 words). Start from something they already know and
  say what is about to be new. No formulas beyond one tiny one.
- "idea": the ONE new idea, max 45 words, short sentences. A picture is shown
  next to it - do not describe what a picture could show. Draw any vector or
  matrix as a small text grid on its own lines.
- "example": a worked example with small numbers, as a list of 3-5 steps.
  Each step is an object {{"step": what is written or computed in this line,
  "why": one short reason}}. ONE operation per step - never skip a line.
- "try_it": a warm-up of the SAME type as the example but with different
  numbers: {{"question": ..., "options": [exactly 3 short answers, only one
  correct], "correct": index of the correct option (0, 1 or 2),
  "explanation": 1-2 sentences why}}. The wrong options must be the typical
  beginner mistakes, not nonsense.

{CONVENTIONS}

Formatting: plain text only inside every string. No LaTeX, no HTML, no
Markdown. Unicode symbols are fine (ρ, ψ, ⟨ ⟩, |0⟩, ², √, †). Write powers
as |a|² and phases as e^(iφ).

Study material (use it as the source of truth):
\"\"\"
{material}
\"\"\"
"""
    raw = ask_json(prompt, temperature=0.4)
    try:
        steps = [{"step": str(x["step"]).strip(), "why": str(x["why"]).strip()}
                 for x in raw["example"] if x.get("step")]
        t = raw["try_it"]
        options = [str(o).strip() for o in t["options"]]
        correct = int(t["correct"])
        cards = {"bridge": str(raw["bridge"]).strip(), "idea": str(raw["idea"]).strip(),
                 "example": steps[:6]}
        if (not cards["bridge"] or not cards["idea"] or len(steps) < 2
                or len(options) < 2 or len(set(options)) != len(options)
                or not 0 <= correct < len(options) or not str(t["question"]).strip()):
            return None
    except (KeyError, TypeError, ValueError, AttributeError):
        return None
    if not objective:
        cards["objective"] = str(raw.get("objective") or "").strip().splitlines()[0:1]
        cards["objective"] = cards["objective"][0] if cards["objective"] else ""
    if figures:
        cards["figure"] = str(raw.get("figure") or "").strip()
        cards["figure_numbers"] = raw.get("figure_numbers")
    right = options[correct]
    random.shuffle(options)
    cards["try_it"] = {"question": str(t["question"]).strip(), "options": options,
                       "correct": options.index(right),
                       "explanation": str(t.get("explanation") or "").strip()}
    return cards


def explain_differently(concept: str, objective: str, text: str) -> str:
    """The learner pressed "I didn't get it". The app shows a real picture
    (drawn by our code); this adds a few plain words to go with it.
    Same content as the card, said more simply - no new facts."""
    prompt = f"""A beginner studying "{concept}" did not understand this explanation:

\"\"\"
{text}
\"\"\"

Say the SAME thing again, more simply:
- Max 45 words. 3 short sentences at most. Everyday words.
- Use the smallest possible numbers if you need any.
- Do NOT write "imagine" or "picture" - a real picture is shown next to
  your text. Do NOT add any fact, symbol or formula that is not in the
  explanation above.

Formatting: plain text only. No LaTeX, no HTML, no Markdown. Unicode symbols
are fine. Write powers as a² (never a^2).
"""
    return ask(prompt, temperature=0.4)
