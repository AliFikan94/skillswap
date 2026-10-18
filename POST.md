---
title: SkillSwap - trade skills, not cash, to start your side hustle
tags: hf26challenge, hacktoberfest, ai, python
---

*This is a submission for the Hacktoberfest 2026 Week 2 challenge (Side Hustle).*

## What I built
Most side hustles stall on money: you need a logo, a landing page or a tutor before you earn anything. SkillSwap lets people trade skills instead. You list what you can teach and what you want to learn, and the app finds direct swaps, multi-way loops (A teaches B, B teaches C, C teaches A) and, if neither exists, lets you pay in time-credits.

## Demo
<!-- add GitHub repo link + screenshot/GIF -->

## How open-source AI is used
A local open-weight model (Gemma via Ollama) turns messy profile text into canonical skills so matching works, and drafts a first-session plan for each swap. Everything is optional and falls back to deterministic code.

## Why open matters here
- **Privacy:** profiles describe what people want to learn; with a local model that never leaves their machine.
- **Cost:** no API bill, which matters for a project about not having cash.
- **Swappable:** change `SKILLSWAP_MODEL` to any Ollama model, no code changes.

## How it works
Skills form a directed graph (edge A->B when B can teach something A wants). Direct matches are 2-cycles, loops are longer simple cycles found by DFS. See `app/matching.py`.
