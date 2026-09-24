"""
Quantum Study Agent - interactive study session
Nebius x NVIDIA Global AI Hackathon 2026 - Personal AI track

Usage:
    python3 app.py --concept density_matrix --material test.txt
    python3 app.py --concept density_matrix --material test.txt --simulate mixed

How a session works:
- Teach first: each level opens with a short lesson card, so a learner who
  has not read the material yet is not thrown straight into questions.
- Difficulty ladder: recall -> apply -> transfer. A level is passed after
  2 correct answers in a row; a wrong answer shows a review page.
- Short sessions: at most 5 questions, then come back another day.
- Type 'hint' for a nudge, 'quit' to stop. Every answer is saved to
  learner_profile.json so the next session picks up where you left off.
"""

import argparse
import random
from pathlib import Path

import profile_store
import tutor

MIN_MATERIAL_CHARS = 200
MAX_TRIES_PER_LEVEL = 2        # wrong answers per level before stopping for the day
DEFAULT_MAX_QUESTIONS = 5      # short daily sessions beat long cramming sessions


def read_material(path: str) -> str:
    file = Path(path)
    if not file.exists():
        raise SystemExit(f"Material file not found: {path}")
    text = file.read_text(encoding="utf-8").strip()
    if len(text) < MIN_MATERIAL_CHARS:
        raise SystemExit(
            f"{path} has only {len(text)} characters. Paste at least "
            f"{MIN_MATERIAL_CHARS} characters of study material first "
            "(no API call was made)."
        )
    return text


def read_answer(question: dict) -> str:
    """Multi-line answer: finish with an empty line.
    'hint' shows a nudge, 'quit' stops the session."""
    print("\nYour answer (empty line = submit | 'hint' = get a nudge | 'quit' = stop):")
    lines = []
    while True:
        line = input()
        command = line.strip().lower()
        if not lines and command == "quit":
            return "quit"
        if not lines and command == "hint":
            print(f"  Hint: {question.get('hint') or 'No hint for this one - try the lesson example.'}")
            continue
        if line == "" and lines:
            break
        if line != "":
            lines.append(line)
    return "\n".join(lines)


def get_answer(question: dict, simulate: str | None) -> str:
    if not simulate:
        return read_answer(question)
    persona = simulate if simulate != "mixed" else random.choice(["strong", "weak"])
    answer = tutor.simulate_answer(question, persona)
    print(f"\n[simulated {persona} student] {answer}")
    return answer


def show_lesson(material: str, concept_name: str, level: int) -> None:
    print(f"\n=== Lesson: {concept_name} - {tutor.DIFFICULTY_NAMES[level]} ===")
    print(tutor.micro_lesson(material, concept_name, level))


def run_session(concept_name: str, material: str, max_questions: int,
                simulate: str | None) -> None:
    profile = profile_store.load()
    concept = profile_store.get_concept(profile, concept_name)

    if concept["status"] == "mastered":
        print(f"'{concept_name}' is already mastered. Starting a review at level 3.")
        level = profile_store.MAX_LEVEL
    else:
        level = concept["level"] + 1

    print(f"\n=== Studying: {concept_name} | level {level} "
          f"({tutor.DIFFICULTY_NAMES[level]}) | up to {max_questions} questions ===")

    need = profile_store.CORRECT_IN_A_ROW_TO_PASS
    tries = 0
    asked: list[str] = []
    lesson_shown_for = None

    while level <= profile_store.MAX_LEVEL:
        if len(asked) >= max_questions:
            print(f"\nThat's {max_questions} questions - enough for today. "
                  f"Next review: {concept['next_review']}. See you then!")
            break

        if lesson_shown_for != level:
            show_lesson(material, concept_name, level)
            lesson_shown_for = level

        weak_points = [h["weak_point"] for h in concept["history"] if h["weak_point"]]
        print(f"\n--- Question {len(asked) + 1}/{max_questions} | Level {level}/3 "
              f"({tutor.DIFFICULTY_NAMES[level]}) | streak {concept['streak']}/{need} ---")
        question = tutor.generate_question(material, concept_name, level,
                                           weak_points, asked)
        asked.append(question["question"])
        print(f"\nQ: {question['question']}")

        answer = get_answer(question, simulate)
        if answer == "quit":
            print("Session stopped. Progress so far is saved.")
            break

        result = tutor.grade_answer(question, answer)
        passed = profile_store.record_attempt(concept, level, result["correct"],
                                              result.get("weak_point"))
        profile_store.save(profile)

        print(f"\n{'CORRECT' if result['correct'] else 'NOT YET'} - {result['feedback']}")

        if result["correct"]:
            if passed:
                print(f"\n>>> Level {level} passed ({need} correct in a row).")
                level += 1
                tries = 0
            else:
                left = need - concept["streak"]
                print(f"\n{left} more correct in a row to pass level {level}.")
            continue

        tries += 1
        print(f"\nModel answer: {question['expected_answer']}")
        print("\n=== Review page ===")
        print(tutor.review_page(material, concept_name,
                                result.get("weak_point") or "", question, answer))

        if tries >= MAX_TRIES_PER_LEVEL:
            print(f"\nLet's stop here for today. '{concept_name}' is scheduled "
                  f"for review on {concept['next_review']}.")
            break
        print("\nTry a new question at the same level.")

    if concept["status"] == "mastered":
        print(f"\n*** '{concept_name}' mastered! Next review: {concept['next_review']} ***")

    profile_store.save(profile)


def main() -> None:
    parser = argparse.ArgumentParser(description="Quantum Study Agent")
    parser.add_argument("--concept", required=True,
                        help="concept name, e.g. density_matrix")
    parser.add_argument("--material", required=True,
                        help="path to a .txt file with the study material")
    parser.add_argument("--max-questions", type=int, default=DEFAULT_MAX_QUESTIONS,
                        help=f"questions per session (default {DEFAULT_MAX_QUESTIONS})")
    parser.add_argument("--simulate", choices=["strong", "weak", "mixed"],
                        help="developer test mode: a simulated student answers "
                             "(uses the real API; writes to a separate profile)")
    args = parser.parse_args()

    if args.simulate:
        # Never mix simulated answers into the real learner's memory.
        profile_store.PROFILE_PATH = Path("learner_profile.simulated.json")
        print("*** TEST MODE: simulated student, saving to "
              "learner_profile.simulated.json ***")

    run_session(args.concept, read_material(args.material),
                args.max_questions, args.simulate)


if __name__ == "__main__":
    main()
