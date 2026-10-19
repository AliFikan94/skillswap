"""Matching engine: direct swaps and multi-way loops over a skill graph.

An edge A -> B means "A wants something B offers", i.e. B can teach A.
A direct match is a 2-cycle (A -> B -> A); a loop match is a longer simple cycle.

What counts as "wants something B offers" is decided by a `similar(offered, wanted)`
predicate: exact equality by default, or embedding similarity (see semantic.py).
"""
from dataclasses import dataclass, field
from typing import Callable

Similar = Callable[[str, str], bool]


def norm(skill: str) -> str:
    return " ".join(skill.lower().split())


def exact(offered: str, wanted: str) -> bool:
    return offered == wanted


@dataclass
class Profile:
    id: int
    name: str
    offers: set[str] = field(default_factory=set)
    wants: set[str] = field(default_factory=set)


def gives(teacher: Profile, learner: Profile, similar: Similar = exact) -> dict[str, str]:
    """Skills `teacher` offers that satisfy something `learner` wants: {offered: wanted}."""
    out = {}
    for offered in sorted(teacher.offers):
        for wanted in sorted(learner.wants):
            if similar(offered, wanted):
                out[offered] = wanted
                break
    return out


def find_cycles(me: Profile, others: list[Profile], max_len: int = 4, similar: Similar = exact):
    """Return simple cycles through `me` as lists of (teacher, learner, {offered: wanted}) hops.

    Cycles of length 2 are direct matches. DFS only follows teacher -> learner edges.
    """
    people = {p.id: p for p in others if p.id != me.id}
    people[me.id] = me
    results = []

    def walk(path: list[Profile]):
        tail = path[-1]
        for cand in people.values():
            skills = gives(tail, cand, similar)  # tail teaches cand
            if not skills:
                continue
            if cand.id == me.id:
                if len(path) >= 2:
                    hops = [(path[i], path[i + 1], gives(path[i], path[i + 1], similar)) for i in range(len(path) - 1)]
                    hops.append((tail, me, skills))
                    results.append(hops)
                continue
            if cand in path or len(path) >= max_len:
                continue
            walk(path + [cand])

    walk([me])
    return results


def match_for(me: Profile, others: list[Profile], max_len: int = 4, similar: Similar = exact) -> dict:
    direct, loops = [], []
    for hops in find_cycles(me, others, max_len, similar):
        steps = [
            {"teacher": t.name, "teacher_id": t.id, "learner": l.name, "learner_id": l.id,
             "skills": sorted(s),
             # only when the match is fuzzy: which of the learner's wants each offer satisfies
             "for": {o: w for o, w in s.items() if o != w}}
            for t, l, s in hops
        ]
        (direct if len(hops) == 2 else loops).append({"size": len(hops), "steps": steps})
    loops.sort(key=lambda c: c["size"])
    return {"direct": direct, "loops": loops}
