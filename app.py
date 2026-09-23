"""
Quantum Study Agent - starter script
Nebius x NVIDIA Global AI Hackathon 2026 - Personal AI track

This calls NVIDIA Nemotron through Nebius Token Factory's
OpenAI-compatible API. Once your Nebius Builder Program application
is approved and you have an API key, put it in a .env file as:

    NEBIUS_API_KEY=your_key_here

Then: pip install openai python-dotenv
"""

import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(
    base_url="https://api.tokenfactory.nebius.com/v1/",
    api_key=os.environ.get("NEBIUS_API_KEY"),
)

MODEL = "nvidia/nemotron-3-super-120b-a12b"  # verify exact model id in your Nebius dashboard


def summarize_and_quiz(text: str) -> str:
    """Take a chunk of study material and return a summary + short quiz."""
    prompt = f"""You are a patient physics/quantum computing tutor helping
an undergraduate EEE student. Given the material below:

1. Summarize the core ideas in plain language (5-8 sentences).
2. Write 3 short quiz questions (with answers hidden below a
   "---ANSWERS---" line) to help the student self-test.

Material:
\"\"\"
{text}
\"\"\"
"""
    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.choices[0].message.content


if __name__ == "__main__":
    sample_text = (
        "Paste a paragraph from a paper or lecture note here to test the agent."
    )
    print(summarize_and_quiz(sample_text))
