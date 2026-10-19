"""Semantic skill matching with a local open-weight embedding model (Ollama).

"ui design" should match "figma" even though the strings differ. Skill names are embedded
with a model running on the user's own machine (default: Gemma's embeddinggemma), vectors
are cached in SQLite, and two skills match when their cosine similarity clears a threshold.

Needs SKILLSWAP_OLLAMA_URL. Without it, or if the model is unreachable, matching falls back
to exact string equality, so the app never depends on the model.
"""
import json
import math
import os
import time
import urllib.request

from .matching import Similar, exact

_down_until = 0.0  # circuit breaker: skip the model briefly after a failure


def _model() -> str:
    return os.environ.get("SKILLSWAP_EMBED_MODEL", "embeddinggemma")


def threshold() -> float:
    return float(os.environ.get("SKILLSWAP_SIM_THRESHOLD", "0.75"))


def _embed_batch(texts: list[str]) -> list[list[float]] | None:
    global _down_until
    url = os.environ.get("SKILLSWAP_OLLAMA_URL")
    if not url or time.time() < _down_until:
        return None
    req = urllib.request.Request(url.rstrip("/") + "/api/embed", json.dumps({"model": _model(), "input": texts}).encode(),
                                 {"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=float(os.environ.get("SKILLSWAP_AI_TIMEOUT", "20"))) as r:
            vecs = json.load(r)["embeddings"]
        if len(vecs) != len(texts) or not all(vecs):
            raise ValueError("unexpected embedding response")
        return vecs
    except Exception:
        _down_until = time.time() + 30
        return None


def _unit(v: list[float]) -> list[float]:
    n = math.sqrt(sum(x * x for x in v)) or 1.0
    return [x / n for x in v]


def vectors(conn, skills) -> dict[str, list[float]]:
    """Unit vectors for as many of `skills` as are cached or can be embedded now."""
    model = _model()
    have = {r["skill"]: json.loads(r["vec"]) for r in
            conn.execute("SELECT skill, vec FROM skill_vectors WHERE model=?", (model,))}
    missing = sorted(set(skills) - have.keys())
    if missing and (fresh := _embed_batch(missing)):
        for s, v in zip(missing, fresh):
            v = _unit(v)
            conn.execute("INSERT OR REPLACE INTO skill_vectors VALUES (?,?,?)", (s, model, json.dumps(v)))
            have[s] = v
        conn.commit()
    return {s: have[s] for s in skills if s in have}


def make_similar(conn, skills, cutoff: float | None = None) -> Similar:
    """A predicate for matching.py: exact match, or cosine similarity >= cutoff."""
    vecs = vectors(conn, skills)
    if not vecs:
        return exact
    cutoff = threshold() if cutoff is None else cutoff

    def similar(offered: str, wanted: str) -> bool:
        if offered == wanted:
            return True
        a, b = vecs.get(offered), vecs.get(wanted)
        return bool(a and b and sum(x * y for x, y in zip(a, b)) >= cutoff)

    return similar
