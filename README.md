# Quantum Study Agent

A personal, stateful study agent for learning quantum computing.
Nebius x NVIDIA Global AI Hackathon 2026 — **Personal AI track**.

## The problem

Asking a chatbot to "quiz me" gives you a one-off quiz and then forgets you.
It doesn't know what you got wrong last week, it never checks whether you
actually did the reading, and it asks recall questions you can answer by
re-reading the text.

## What this agent does differently

- **See it, don't just read it** — the web app's Explore tab puts any one-qubit
  state on a Bloch sphere next to its density-matrix heat map. Mix two states
  with a slider and watch the mixture move along the straight line between
  them, inside the sphere, while the coherence and purity drop live. These
  numbers are computed exactly (numpy), not by the AI.
- **A learning path that starts from the basics** — state vectors → outer
  products → pure-state density matrices → mixed states. Each step has its own
  short built-in primer. A step unlocks when the one before it is mastered
  (all three levels passed): unlocking the next step is the reward. The agent
  recommends what to study now — a due review first, otherwise the next step
  on your path. Already know the basics? Turn on "skip ahead".
- **Teach first, then ask** — each level opens with a short lesson card
  (max ~120 words, one idea, one tiny worked example, matrices drawn as text
  grids). It assumes you have *not* read the material yet.
- **Short rounds, your choice** — a round is at most 5 questions. After each
  round you choose: *keep going* (another round; if you just mastered a step,
  the next step on your path) or *done for today*, which gives you homework
  once for the whole sitting.
- **Hints** — type `hint` for a nudge toward the method without the answer.
- **Difficulty ladder** — questions climb from *recall* → *apply* (a small
  calculation) → *transfer* (a situation not in the material). You move up
  only after **2 correct answers in a row** at a level — one lucky answer is
  not proof of understanding. Each new question tests the idea from a
  different angle, never repeating one already asked.
- **Review pages** — when you get stuck, the agent names the exact gap
  (e.g. "purity test tr(ρ²)") and writes a short focused review before you
  try again.
- **Homework with real, checked resources** — every session ends with a short
  assignment tied to the gap the agent found. Resources cannot be invented by
  the model: book sections come from a fixed list checked against the book's
  table of contents (Nielsen & Chuang), and web resources are found live with
  the **Tavily Search API**, restricted to trusted educational sites
  (Wikipedia, IBM Quantum Learning, PennyLane, arXiv, university courses, …).
  Our own code then opens every link and keeps only the ones that load. The
  model only *picks* from these lists by number.
- **Did you really do the homework?** — each assignment stores two check
  questions. When you say "I did it", the agent asks them and grades your
  answers. Both right: homework done. Otherwise it stays open, and the gap it
  found is fed into your next practice questions.
- **Welcome back** — every session starts with what is waiting for you:
  homework to check and spaced-repetition reviews that are due.
- **Memory that stays with you** — every attempt, weak point and review date
  is saved to a local `learner_profile.json`. The model itself is stateless;
  the agent's memory lives in this file, on your machine, and is never pushed
  to GitHub.
- **Spaced repetition** — mastered concepts come back for review after a few
  days, missed ones sooner.

## Roadmap

- [x] Week 1 — Nebius Token Factory + Nemotron connection
- [x] Week 2 — interactive difficulty ladder, answer grading, learner profile,
      teach-first lessons, short sessions, hints, simulated-student test mode
- [x] Week 3 (part 1) — Streamlit web app: Explore tab (Bloch sphere, heat
      map, live mixing slider), Study tab (full tutor loop), downloadable
      learner profile, access code to protect API credits
- [x] Week 3 (part 2) — learning path that starts from the basics
      (4 steps, unlock-on-mastery, "what to study now" recommendation)
- [x] Week 4 (part 1) — homework: checked book sections + Tavily web search on
      trusted sites + code-verified links
- [x] Week 4 (part 2) — homework check questions, session start review
- [ ] Next — keep the learner profile across visits without manual download
- [ ] Week 5 — a week of real daily use; demo built from real progress data

## Tech stack

- Python
- Streamlit, Plotly, NumPy
- Tavily Search API (web resources for homework)
- NVIDIA Nemotron (`nvidia/nemotron-3-super-120b-a12b`) via Nebius Token Factory
  (OpenAI-compatible API)

## Setup

```
pip3 install openai python-dotenv
```

Create a `.env` file (never commit this):

```
NEBIUS_API_KEY=your_key_here
TAVILY_API_KEY=tvly-...   # optional, for web resources in homework
```

## Run the web app

```
pip3 install -r requirements.txt
streamlit run streamlit_app.py
```

On Streamlit Community Cloud, add two secrets (Settings → Secrets):

```
NEBIUS_API_KEY = "your_key_here"
TAVILY_API_KEY = "tvly-..."
ACCESS_CODE = "a code you give to the judges"
```

`TAVILY_API_KEY` is optional: without it, homework uses the book list only.

The access code keeps strangers from spending the API credits on the public
demo. Locally, without secrets, the app opens directly.

## Run in the terminal

Follow the learning path (the agent picks the step):

```
python3 app.py
python3 app.py --concept outer_product        # or choose a step yourself
```

Or study your own text — paste at least 200 characters into `test.txt`:

```
python3 app.py --concept my_topic --material test.txt
```

Type your answer, then press Enter on an empty line to submit.
Type `hint` for a nudge, `quit` to stop — progress is saved after every answer.

Options:

```
--max-questions 8          # longer session (default 5)
--simulate strong|weak|mixed
```

`--simulate` is a developer test mode: a simulated student answers the
questions so the whole loop (lessons, grading, review pages, streaks) can be
checked without typing. It uses the real API and saves to a separate
`learner_profile.simulated.json`, so it never touches the real learner's memory.

## Project structure

| File | Role |
|---|---|
| `streamlit_app.py` | Web app: Explore / Study / My progress tabs |
| `quantum_viz.py` | Exact qubit math + Bloch sphere and heat-map figures |
| `homework.py` | Builds the end-of-session assignment and saves it to the profile |
| `resources.py` | Checked book sections, Tavily search on trusted sites, link checking |
| `curriculum.py` | Learning path: step order, unlocking, what to study now |
| `materials/*.txt` | Built-in primers, one per path step |
| `app.py` | Study session loop (command line) |
| `tutor.py` | Question generation, grading, review pages |
| `profile_store.py` | Learner profile: load, save, difficulty ladder, review dates |
| `llm.py` | Nemotron client and JSON parsing |

## Author

Yasemin Serce — first-year EEE student, Koç University.

## License

MIT
