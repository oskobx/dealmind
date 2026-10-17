"""Tone labeler (§6.2): one short Nano call per negotiator message, one word back."""

from __future__ import annotations

import re

from dealmind import config, llm
from dealmind.suppliers import TONES

# §6.2 prompt, verbatim. Kept byte-identical across calls so the prefix caches (crusoe-skill.md §8).
TONE_PROMPT = "Label the tone of this negotiation message as firm, cooperative, or neutral. Answer with one word."


def normalize_label(text: str) -> str:
    for word in re.findall(r"[a-z]+", text.lower()):
        if word in TONES:
            return word
    return "neutral"


def label_tone(message: str) -> str:
    messages = [
        {"role": "system", "content": TONE_PROMPT},
        {"role": "user", "content": message},
    ]
    try:
        text = llm.chat("tone", config.MODEL_TONE, messages, max_tokens=20, seed=0)
    except llm.LLMError:
        return "neutral"
    return normalize_label(text)
