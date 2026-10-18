"""Optional open-weight model layer (Ollama, e.g. Gemma) running on the user's own machine.

Enabled by setting SKILLSWAP_OLLAMA_URL (e.g. http://localhost:11434). Every function
degrades to a deterministic fallback when the model is off or unreachable, so the
app never depends on it.
"""
import json
import os
import urllib.request

from .matching import norm


def _generate(prompt: str, want_json: bool = False) -> str | None:
    url = os.environ.get("SKILLSWAP_OLLAMA_URL")
    if not url:
        return None
    body = {"model": os.environ.get("SKILLSWAP_MODEL", "gemma3"), "prompt": prompt, "stream": False}
    if want_json:
        body["format"] = "json"
    req = urllib.request.Request(url.rstrip("/") + "/api/generate", json.dumps(body).encode(),
                                 {"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=float(os.environ.get("SKILLSWAP_AI_TIMEOUT", "20"))) as r:
            return json.load(r).get("response")
    except Exception:
        return None


def canonicalize(skills: list[str]) -> list[str]:
    """Map free-text skills to short canonical names so 'I do React stuff' matches 'react'."""
    cleaned = [norm(s) for s in skills if s.strip()]
    if not cleaned:
        return []
    out = _generate(
        'Rewrite each skill as a short canonical lowercase name (1-3 words, no filler). '
        'Return JSON {"skills": [...]} with exactly one entry per input, same order.\n'
        + json.dumps(cleaned), want_json=True)
    try:
        result = [norm(str(x)) for x in json.loads(out)["skills"]]
        if len(result) == len(cleaned) and all(result):
            return result
    except Exception:
        pass
    return cleaned


def swap_plan(teacher: str, learner: str, skill: str) -> dict:
    """A short starter plan for the first session of a side-hustle skill swap."""
    text = _generate(
        f"{teacher} will teach {learner} the skill '{skill}' in a skill swap, so {learner} can use it "
        "for a side hustle. Write a friendly 3-step plan for a first 1-hour session, 60 words max.")
    if text:
        return {"plan": text.strip(), "source": "model"}
    return {"plan": f"1) 10 min: {learner} shares their side-hustle goal. 2) 40 min: {teacher} walks through the "
                    f"basics of {skill} on a real task. 3) 10 min: agree on homework and the next session.",
            "source": "template"}
