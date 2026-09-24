# Quantum Study Agent

A personal, stateful study agent for learning quantum computing.
Nebius x NVIDIA Global AI Hackathon 2026 — **Personal AI track**.

## The problem

Asking a chatbot to "quiz me" gives you a one-off quiz and then forgets you.
It doesn't know what you got wrong last week, it never checks whether you
actually did the reading, and it asks recall questions you can answer by
re-reading the text.

## What this agent does differently

- **Difficulty ladder** — questions climb from *recall* → *apply* (a small
  calculation) → *transfer* (a situation not in the material). You move up
  only after **2 correct answers in a row** at a level — one lucky answer is
  not proof of understanding. Each new question tests the idea from a
  different angle, never repeating one already asked.
- **Review pages** — when you get stuck, the agent names the exact gap
  (e.g. "purity test tr(ρ²)") and writes a short focused review before you
  try again.
- **Memory that stays with you** — every attempt, weak point and review date
  is saved to a local `learner_profile.json`. The model itself is stateless;
  the agent's memory lives in this file, on your machine, and is never pushed
  to GitHub.
- **Spaced repetition** — mastered concepts come back for review after a few
  days, missed ones sooner.

## Roadmap

- [x] Week 1 — Nebius Token Factory + Nemotron connection
- [x] Week 2 — interactive difficulty ladder, answer grading, learner profile
- [ ] Week 3 — per-concept mastery tracking across sessions, session start review
- [ ] Week 4 — assignments (book sections + web resources verified with search),
      follow-up check questions, web UI
- [ ] Week 5 — a week of real daily use; demo built from real progress data

## Tech stack

- Python
- NVIDIA Nemotron (`nvidia/nemotron-3-super-120b-a12b`) via Nebius Token Factory
  (OpenAI-compatible API)

## Setup

```
pip3 install openai python-dotenv
```

Create a `.env` file (never commit this):

```
NEBIUS_API_KEY=your_key_here
```

## Run

Paste at least 200 characters of study material into `test.txt`, then:

```
python3 app.py --concept density_matrix --material test.txt
```

Type your answer, then press Enter on an empty line to submit.
Type `quit` to stop — progress is saved after every answer.

## Project structure

| File | Role |
|---|---|
| `app.py` | Study session loop (command line) |
| `tutor.py` | Question generation, grading, review pages |
| `profile_store.py` | Learner profile: load, save, difficulty ladder, review dates |
| `llm.py` | Nemotron client and JSON parsing |

## Author

Yasemin Serce — first-year EEE student, Koç University.

## License

MIT
