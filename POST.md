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
A local open-weight embedding model (`embeddinggemma` via Ollama) is what makes matching work: it embeds every skill so "ui design" matches "figma" and "I do React stuff" matches "react", which exact string matching can never do. A Gemma chat model also drafts a first-session plan for each swap. Everything falls back to exact matching if the model is off.

## Why open matters here
- **Privacy:** profiles describe what people want to learn; with a local model that never leaves their machine.
- **Cost:** no API bill, which matters for a project about not having cash.
- **Swappable:** change `SKILLSWAP_MODEL` to any Ollama model, no code changes.

## How it works
Skills form a directed graph (edge A->B when B offers something semantically close to what A wants, cosine similarity over local embeddings). Direct matches are 2-cycles, loops are longer simple cycles found by DFS. See `app/matching.py` and `app/semantic.py`.
