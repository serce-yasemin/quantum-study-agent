# Quantum Study Agent

Nebius x NVIDIA Global AI Hackathon 2026 submission — Personal AI track.

## What it does

A personal research/study assistant for learning quantum computing. Feed it a paper or lecture excerpt (e.g. from Prof. Mustecaplioglu's work on quantum thermodynamics), and it:

- Summarizes the core ideas at an undergraduate level
- Generates a short quiz to self-test understanding
- Answers follow-up questions about the material

Built as a genuinely personal tool: I use it myself to study for the IBM Quantum Learning series and prep for my QuEST research position.

## Why this track

Runs entirely on Nebius Token Factory calling an NVIDIA open model (Nemotron) — no physical hardware required, which fits a Personal AI / software-agent submission.

## Tech stack

- Python
- Nebius Token Factory (OpenAI-compatible API)
- NVIDIA Nemotron model

## Status

In progress — built during the Nebius x NVIDIA Global AI Hackathon (submissions through Oct 30, 2026).

## Setup

```
pip install openai python-dotenv
```

Create a `.env` file (never commit this):
```
NEBIUS_API_KEY=your_key_here
```

Run:
```
python app.py
```

## Author

Yasemin Serce — first-year EEE student, Koc University.
