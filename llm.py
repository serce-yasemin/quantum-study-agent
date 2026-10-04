"""
Thin wrapper around NVIDIA Nemotron on Nebius Token Factory.

The model itself is stateless: every call starts from zero. Anything the
agent "remembers" must be passed back in through the prompt. That memory
lives in learner_profile.json (see profile_store.py), not in the model.
"""

import json
import os
import re

from dotenv import load_dotenv
from openai import BadRequestError, OpenAI

load_dotenv()

MODEL = "nvidia/nemotron-3-super-120b-a12b"

_client = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        api_key = os.environ.get("NEBIUS_API_KEY")
        if not api_key:
            raise RuntimeError(
                "NEBIUS_API_KEY is missing. Put it in a .env file next to app.py."
            )
        _client = OpenAI(
            base_url="https://api.tokenfactory.nebius.com/v1/",
            api_key=api_key,
        )
    return _client


# How much the model "thinks" before it answers. Thinking costs time.
# Set NEMOTRON_REASONING to "low" or "off" to trade some care for speed;
# leave it unset for the model's default. (NVIDIA documents these switches
# for Nemotron 3 Super as chat_template_kwargs.)
REASONING = {"off": {"enable_thinking": False},
             "low": {"enable_thinking": True, "low_effort": True}}
_reasoning_refused = False


def _complete(prompt: str, temperature: float):
    global _reasoning_refused
    request = dict(model=MODEL, messages=[{"role": "user", "content": prompt}],
                   temperature=temperature)
    mode = REASONING.get(os.environ.get("NEMOTRON_REASONING", "").strip().lower())
    if mode and not _reasoning_refused:
        try:
            return _get_client().chat.completions.create(
                **request, extra_body={"chat_template_kwargs": mode})
        except BadRequestError:
            _reasoning_refused = True    # the provider does not take the switch
    return _get_client().chat.completions.create(**request)


def ask(prompt: str, temperature: float = 0.4) -> str:
    """Send one prompt, return the model's text reply."""
    response = _complete(prompt, temperature)
    text = response.choices[0].message.content or ""
    # Some reasoning models wrap their thinking in <think> tags; drop it.
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
    # The terminal shows raw text, so stray Markdown bold markers are noise.
    return tidy(text.replace("**", "")).strip()


_SUPERSCRIPT = str.maketrans("0123456789", "⁰¹²³⁴⁵⁶⁷⁸⁹")


def tidy(text: str) -> str:
    """Last line of defence against LaTeX leftovers the prompts forbid:
    |a|^2 or |a|^{2} -> |a|²,  e^{iφ} -> e^(iφ)."""
    text = re.sub(r"\^\{?([0-9]+)\}?", lambda m: m.group(1).translate(_SUPERSCRIPT), text)
    return re.sub(r"\^\{([^{}]*)\}", r"^(\1)", text)          # e^{iπ/3} -> e^(iπ/3)


def ask_json(prompt: str, temperature: float = 0.4) -> dict:
    """Ask for a JSON object and parse it. Retries once if parsing fails."""
    for _ in range(2):
        text = ask(prompt + "\n\nRespond with ONE valid JSON object and nothing else.",
                   temperature)
        match = re.search(r"\{.*\}", text, flags=re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass
    raise ValueError(f"Model did not return valid JSON. Last reply:\n{text}")
