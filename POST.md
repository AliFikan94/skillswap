---
title: Nobody Has Startup Cash. Everybody Has a Skill.
published: false
tags: hf26challenge, hacktoberfest, ai, opensource
---

*This is a submission for the [Hacktoberfest 2026 Week 2 Challenge: Side Hustle](https://dev.to/challenges/hacktoberfest-week2-2026-10-12)*

## What I built

**SkillSwap**: a network where side hustlers pay each other in skills instead of cash.

You list what you can teach and what you want to learn. SkillSwap finds your swap. If nobody wants exactly what you offer, it finds a **loop**: Ada designs Carla's logo, Carla teaches Ben Spanish, Ben teaches Ada Python. Three people, zero dollars, everyone leaves with what they needed.

![A three-way loop on the Discover page](ADD_SCREENSHOT_URL_1)

## How I got there

**Understand.** A side hustle runs on nights and weekends. The people running one are time-poor and cash-poor, but skill-rich. The wall they hit is rarely the idea. It's the one skill they don't have, and the money to buy it.

**Observe.** Look at how people patch that gap today: asking favours in group chats, paying a freelancer they can't really afford, or trying a one-to-one trade that only works when two people happen to need each other's exact thing. Almost nobody gets a clean match.

**Redefine.** The question changed from *"how do I find a cheaper freelancer?"* to *"how might skills pay for skills, even when the trade isn't between two people?"* That reframing is where the loop idea came from.

**Ideate, with Claude.** I used Claude as a thinking partner to argue through options: a marketplace, a time-credit currency, graph-based matching. We kept the combination (swaps first, loops second, credits as a safety net). Claude also spotted the flaw that shaped the AI half of the project: *"figma"* and *"ui design"* are different strings, so exact matching would miss the people who most need each other.

**Prototype.** FastAPI and SQLite, a graph search that finds swaps and loops, real accounts, and a macOS-inspired interface with dark mode. Built with Claude Code.

**Test.** 17 automated tests, plus driving the real app in a browser from sign-up to booking to review. That surfaced bugs I'd have shipped: a broken phone layout, ratings that didn't refresh, a sentence that read "You teaches Ben." One honest caveat: the similarity threshold for fuzzy matches is a starting point, not something I've tuned on real users.

![Fuzzy match: figma ≈ ui design](ADD_SCREENSHOT_URL_2)

## Why open-source AI is the point

Skill profiles say what people *can't* do yet. That's personal. So the matching runs on **Gemma's embedding model (`embeddinggemma`) through Ollama, on your own machine**. Your profile never leaves your laptop, there's no API bill (fitting, for a project about not having cash), and swapping models is one environment variable.

It also degrades gracefully: no model running means exact matching, and the app still works.

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

Your side hustle doesn't need a budget. It needs the right two other people.
