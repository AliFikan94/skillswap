---
title: Nobody Has Startup Cash. Everybody Has a Skill.
published: false
tags: hf26challenge, hacktoberfest, ai, opensource
---

*This is a submission for the [Hacktoberfest 2026 Week 2 Challenge: Side Hustle](https://dev.to/challenges/hacktoberfest-week2-2026-10-12)*

## Your side hustle doesn't have a budget problem. It has a missing-skill problem.

You've got the idea. You've got the weekends. What you don't have is a logo, a landing page, or someone to explain Python to you, and no cash to buy any of it.

Meanwhile, the person who could do that logo in an hour needs exactly what *you* know.

**SkillSwap** connects the two of you. Then it goes further.

## The trick: loops

Direct swaps are easy to imagine and rare in real life. Almost nobody wants *exactly* what you offer. So SkillSwap searches for **loops**:

> Ada designs Carla's logo. Carla teaches Ben Spanish. Ben teaches Ada Python.

Three strangers, zero dollars, everyone walks away with the skill they were missing. No two of them could have traded directly. Together, they can.

![A three-way loop on the Discover page](ADD_SCREENSHOT_URL_1)

No match yet? Teach for an hour, earn a credit, spend it with anyone. The network never leaves you stuck.

## How I got there

**Understand.** A side hustle runs on nights and weekends. The people running one are time-poor and cash-poor, but skill-rich. The wall they hit is rarely the idea. It's the one skill they don't have, and the money to buy it.

**Observe.** Look at how people patch that gap today: asking favours in group chats, paying a freelancer they can't really afford, or attempting a one-to-one trade that only works when two people happen to need each other's exact thing. Clean matches are the exception.

**Redefine.** The question changed from *"how do I find a cheaper freelancer?"* to *"how might skills pay for skills, even when the trade isn't between two people?"* One sentence, and the whole product shifted from a marketplace to a graph.

**Ideate, with Claude.** I used Claude as a sparring partner: marketplace, time-credit currency, graph matching, which wins? We kept all three in order of preference (swaps, then loops, then credits as a safety net). Claude also found the flaw that shaped the AI half of the project: *"figma"* and *"ui design"* are different strings, so exact matching would miss the very people who most need each other.

**Prototype.** FastAPI and SQLite, a graph search for swaps and loops, real accounts, and an interface that feels like it belongs on a Mac, dark mode included. Built with Claude Code.

**Test.** 17 automated tests, plus driving the real app in a browser from sign-up to booking to review. That caught things I'd have happily shipped: a phone layout that fell apart, ratings that didn't refresh, and a loop card that cheerfully announced "You teaches Ben." One honest caveat: the similarity threshold for fuzzy matches is a starting point, not something I've tuned on real users yet.

## The open-source part isn't decoration. It's the engine.

Type "ui design" and the best teacher on the network might list "figma". Matching those takes meaning, not string equality.

So SkillSwap embeds every skill with **Gemma's embedding model (`embeddinggemma`), running through Ollama on your own machine**, and matches by similarity. The result shows up right in the interface:

![Fuzzy match: figma ≈ ui design](ADD_SCREENSHOT_URL_2)

Why local and open matters here:

- **Privacy.** A skill profile is a list of what you *can't* do yet. That's personal. It never leaves your laptop.
- **Cost.** No API bill, for a project about not having cash.
- **Control.** Swap the model with one environment variable. Tune the threshold. Change the behaviour.
- **Resilience.** No model running? The app falls back to exact matching and keeps working.

## Try it

Code: **[AliFikan94/skillswap](https://github.com/AliFikan94/skillswap/tree/claude/eloquent-gates-c2q636)**

```bash
git clone https://github.com/AliFikan94/skillswap.git && cd skillswap
git checkout claude/eloquent-gates-c2q636
pip install -r requirements.txt && python -m app.seed
ollama pull embeddinggemma            # optional: semantic matching
SKILLSWAP_OLLAMA_URL=http://localhost:11434 uvicorn app.main:app
```

Sign in as `ada@demo.test` / `demo12345`.

## What's next

Real scheduling, in-app chat, and a notification the moment a new loop closes around you.

Because the best side hustle advice might just be this: you don't need a budget. You need the right two other people.
