"""
Quantum Study Agent - interactive study session (Week 2)
Nebius x NVIDIA Global AI Hackathon 2026 - Personal AI track

Usage:
    python3 app.py --concept density_matrix --material test.txt

The agent climbs a difficulty ladder (recall -> apply -> transfer).
Correct answer: move up one level. Wrong answer: read a short review
page, then try a new question at the same level. Every attempt is saved
to learner_profile.json so the next session can pick up where you left off.
"""

import argparse
from pathlib import Path

import profile_store
import tutor

MIN_MATERIAL_CHARS = 200
MAX_TRIES_PER_LEVEL = 2  # keeps a stuck session from burning API credits


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


def read_answer() -> str:
    """Multi-line answer: finish with an empty line. Type 'quit' to stop."""
    print("\nYour answer (press Enter on an empty line to submit, 'quit' to stop):")
    lines = []
    while True:
        line = input()
        if line.strip().lower() == "quit" and not lines:
            return "quit"
        if line == "" and lines:
            break
        if line != "":
            lines.append(line)
    return "\n".join(lines)


def run_session(concept_name: str, material: str) -> None:
    profile = profile_store.load()
    concept = profile_store.get_concept(profile, concept_name)

    if concept["status"] == "mastered":
        print(f"'{concept_name}' is already mastered. Starting a review at level 3.")
        level = profile_store.MAX_LEVEL
    else:
        level = concept["level"] + 1

    print(f"\n=== Studying: {concept_name} | starting at level {level} "
          f"({tutor.DIFFICULTY_NAMES[level]}) ===")

    tries = 0
    while level <= profile_store.MAX_LEVEL:
        weak_points = [h["weak_point"] for h in concept["history"] if h["weak_point"]]
        print(f"\n--- Level {level}/3 ({tutor.DIFFICULTY_NAMES[level]}) ---")
        question = tutor.generate_question(material, concept_name, level, weak_points)
        print(f"\nQ: {question['question']}")

        answer = read_answer()
        if answer == "quit":
            print("Session stopped. Progress so far is saved.")
            break

        result = tutor.grade_answer(question, answer)
        profile_store.record_attempt(concept, level, result["correct"],
                                     result.get("weak_point"))
        profile_store.save(profile)

        print(f"\n{'CORRECT' if result['correct'] else 'NOT YET'} - {result['feedback']}")

        if result["correct"]:
            level += 1
            tries = 0
            continue

        tries += 1
        print(f"\nModel answer: {question['expected_answer']}")
        print("\n=== Review page ===")
        print(tutor.review_page(material, concept_name, result.get("weak_point") or ""))

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
    args = parser.parse_args()

    run_session(args.concept, read_material(args.material))


if __name__ == "__main__":
    main()
