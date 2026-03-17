"""Shared utility functions."""

import re

_JSON_FENCE_RE = re.compile(r"```(?:json)?\s*\n(.*?)\n\s*```", re.DOTALL)


def extract_json(text: str) -> str:
    """Extract JSON from AI response, handling markdown code fences and preamble."""
    # Try to find JSON inside ```json ... ``` fences
    match = _JSON_FENCE_RE.search(text)
    if match:
        return match.group(1).strip()

    # Try to find raw JSON object (first { to last })
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        return text[start : end + 1]

    # Fallback: return as-is and let Pydantic raise a clear error
    return text
