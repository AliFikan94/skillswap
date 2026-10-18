"""Matching engine: direct swaps and multi-way loops over a skill graph.

An edge A -> B means "A wants something B offers", i.e. B can teach A.
A direct match is a 2-cycle (A -> B -> A); a loop match is a longer simple cycle.
"""
from dataclasses import dataclass, field


def norm(skill: str) -> str:
    return " ".join(skill.lower().split())


@dataclass
class Profile:
    id: int
    name: str
    offers: set[str] = field(default_factory=set)
    wants: set[str] = field(default_factory=set)


def _gives(teacher: Profile, learner: Profile) -> set[str]:
    return teacher.offers & learner.wants


def find_cycles(me: Profile, others: list[Profile], max_len: int = 4) -> list[list[tuple[Profile, Profile, set[str]]]]:
    """Return simple cycles through `me` as lists of (teacher, learner, skills) hops.

    Cycles of length 2 are direct matches. Each cycle is reported once per
    direction of travel; DFS only follows teacher -> learner edges.
    """
    people = {p.id: p for p in others if p.id != me.id}
    people[me.id] = me
    results = []

    def walk(path: list[Profile]):
        tail = path[-1]
        for cand in people.values():
            skills = _gives(tail, cand)  # tail teaches cand
            if not skills:
                continue
            if cand.id == me.id:
                if len(path) >= 2:
                    hops = [(path[i], path[i + 1], _gives(path[i], path[i + 1])) for i in range(len(path) - 1)]
                    hops.append((tail, me, skills))
                    results.append(hops)
                continue
            if cand in path or len(path) >= max_len:
                continue
            walk(path + [cand])

    walk([me])
    return results


def match_for(me: Profile, others: list[Profile], max_len: int = 4) -> dict:
    direct, loops = [], []
    for hops in find_cycles(me, others, max_len):
        steps = [
            {"teacher": t.name, "teacher_id": t.id, "learner": l.name, "learner_id": l.id, "skills": sorted(s)}
            for t, l, s in hops
        ]
        (direct if len(hops) == 2 else loops).append({"size": len(hops), "steps": steps})
    # DFS yields a cycle once per starting direction; direct matches are unique per partner.
    loops.sort(key=lambda c: c["size"])
    return {"direct": direct, "loops": loops}
