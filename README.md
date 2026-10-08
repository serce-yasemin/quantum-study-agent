# Quantum Study Agent

A personal, stateful study agent for learning quantum computing.
Nebius x NVIDIA Global AI Hackathon 2026 — **Personal AI track**.

**Live app:** https://quantum-study-agent.streamlit.app

> **For judges:** the access code and a demo account are in the submission's
> testing instructions. The 🔭 Explore tab is computed by the app itself and
> always works. The AI tutor (📘 Study) runs on shared model credits; if they
> ever run out, the app says so politely and the demo video shows the tutor
> in action.

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
- **Hands-on labs** — the Explore tab also has a gate circuit (up to four
  gates, the state followed step by step on the sphere, and what the whole
  circuit amounts to: H·Z·H = X), a measurement lab (measure 1, 10 or 100
  times and watch the counts approach the predicted probabilities, in the
  Z, X or Y basis), a two-qubit correlation lab (Bell states agree in both
  bases, product states do not) and a step-by-step Bell-state builder.
- **A learning path that starts from the basics** — state vectors → outer
  products → pure-state density matrices → mixed states → the Bloch sphere →
  single-qubit gates (X, Z, H) → measuring in other bases → two qubits and
  tensor products → entanglement and Bell states → the reduced density
  matrix. Each step has its own
  short built-in primer. A step unlocks when the one before it is mastered
  (all three levels passed): unlocking the next step is the reward. The agent
  recommends what to study now — a due review first, otherwise the next step
  on your path. Already know the basics? Turn on "skip ahead".
- **Teach first, then ask** — each level opens with a lesson in four small
  cards, one at a time: *you already know* → *the new idea* (next to an
  interactive figure drawn by our own code) → *a worked example*, one
  operation per line with its reason → *your turn*, a multiple-choice warm-up
  that does not count for your level. Every card has an "I didn't get it"
  button that explains the same thing more simply, with an everyday
  comparison. The model writes the cards; code checks their shape, shuffles
  the answer options, and falls back to a plain lesson if anything is off.
- **Fast to start** — the goal, the four cards and an easier wording of each
  card ("I didn't get it") come from one model call. A lesson you have seen
  is kept and opens at once. The lesson you will probably open next (the
  recommended step, the next level) and the first question are written in the
  background while you read. Optional: set `NEMOTRON_REASONING` to `low` or
  `off` to make the model think less before it answers.
- **Answering is easy** — a question with parts (a), (b), (c) gets one box per
  part. No special symbols needed: a plain keyboard (psi, sqrt(2), <phi|psi>)
  is accepted, and a small ➕ picker adds ψ, φ, √ … for you.
- **Points, levels, badges, streak** — +1 for finishing a lesson, +1 for a
  right warm-up, +1 / +2 / +3 for a correct answer at level 1 / 2 / 3. Points
  add up to named levels (Curious → Qubit Rookie → … → Quantum Navigator), each
  with a badge. Days in a row with at least one point make a streak; every 7
  days in a row bring bonus points (7 days +10, 14 days +20, …).
- **The picture belongs to the lesson** — each concept has a small catalogue
  of pictures drawn by our own code. The model never draws: it only picks the
  one that fits the idea it teaches (or none), and code checks the pick.
- **Study as long as you like** — there is no question limit. *Finish for
  today* is always there; when you press it you choose between carrying on
  and getting homework. Two misses at a level send you back to the lesson
  cards for another look instead of ending the session. If you just mastered
  a step, *keep going* moves you to the next one.
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
  answers. Both right: homework done. One wrong: one more question on that
  idea, to tell a slip from a real gap - right means done; wrong means a short
  review page on exactly what is missing. Both wrong: the review page straight
  away. While homework stays open, the gap is fed into your next practice
  questions.
- **Welcome back** — every session starts with what is waiting for you:
  homework to check and spaced-repetition reviews that are due.
- **Memory that stays with you** — sign in with e-mail + password and your
  learner profile (every attempt, weak point, review date and homework) is
  saved to your account after every step, so you can continue on any device.
  Forgot your password? The app e-mails you a reset link.
  The device stays signed in for 7 days, and a lesson or question you were
  in the middle of is waiting where you stopped - even after the screen went
  to sleep. *Sign out* forgets the device.
  The model itself is stateless; the agent's memory is this profile. It is
  stored in Supabase with row-level security: each learner can read and write
  only their own row. Without an account set up (e.g. locally), the profile
  stays in the browser session and can be downloaded as JSON.
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
- [x] Learner accounts: profile saved to Supabase, works on any device;
      password reset by e-mail
- [x] Homework check with a follow-up question and review page; lesson
      cards with figures, warm-up and points
- [x] Path steps 5 and 6: the Bloch sphere, single-qubit gates X, Z, H
- [x] Path steps 7 to 10: measuring in other bases, two qubits and tensor
      products, entanglement and Bell states, the reduced density matrix
- [x] Stay signed in, continue where you stopped, display name, answer boxes
      per question part, symbol picker, faster lesson start
- [ ] Week 5 — a week of real daily use; demo built from real progress data

## Tech stack

- Python
- Streamlit, Plotly, NumPy
- Supabase (accounts + profile storage, row-level security)
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

On Streamlit Community Cloud, add these secrets (Settings → Secrets):

```
NEBIUS_API_KEY = "your_key_here"
TAVILY_API_KEY = "tvly-..."
SUPABASE_URL = "https://<project>.supabase.co"
SUPABASE_KEY = "sb_publishable_..."
ACCESS_CODE = "a code you give to the judges"
```

The Supabase project needs one table, `learner_profiles` (`user_id` uuid
primary key → `auth.users`, `profile` jsonb, `updated_at` timestamptz), with
row-level security policies that allow a learner to select, insert and update
only the row where `user_id = auth.uid()`.

E-mail links (sign-up confirmation, password reset) must open the app with the
token in the query string, because a Streamlit app cannot read the `#...`
part of a URL. In Supabase → Authentication:

- URL Configuration → Site URL: the app's address
- Emails → "Confirm signup" template link:
  `{{ .SiteURL }}/?token_hash={{ .TokenHash }}&type=email`
- Emails → "Reset password" template link:
  `{{ .SiteURL }}/?token_hash={{ .TokenHash }}&type=recovery`
- Emails → SMTP Settings: a real mail server. Supabase's built-in server only
  delivers to members of the project's team, so other learners would never
  get the e-mails.

`TAVILY_API_KEY` is optional: without it, homework uses the book list only.

The access code keeps strangers from spending the API credits on the public
demo. Locally, without secrets, the app opens directly. Optional secrets:

- `JUDGE_ACCESS_CODE` — a second code (for the hackathon judges) that can be
  switched off on its own.
- `DAILY_CALL_LIMIT` — model calls each account may start per day (default
  200; a full study session uses roughly 25-40). When it is reached, the
  tutor says so and the Explore tab keeps working.

If the model credits run out, the app shows a plain message instead of an
error trace.

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
| `labs.py` | Explore-tab labs: gate circuit, measurement, two-qubit correlations |
| `ui.py` | Card grids that wrap to the window width (readable on a phone) |
| `quantum_viz.py` | Exact qubit math + Bloch sphere and heat-map figures |
| `figures.py` | Catalogue of lesson pictures the model may pick from |
| `rewards.py` | Points → levels, badges, daily streak and streak bonus |
| `store.py` | Learner accounts (Supabase Auth) and saving the profile |
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
