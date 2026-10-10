# skills.md — build journey & tools

## Team & problem
**Problem 2 — Global Context: Memory Across Channels.** Goal: VANI already knows the buyer or seller, and their
history, before it speaks — and resumes the conversation across voice, WhatsApp, chat and app.

## Build journey

| Step | What we did | What we learned / decided |
|---|---|---|
| 1. Read the data | Profiled all 11 seller files (5,000 sellers, ~320k events) and the buyer `getContext` export | The buyer export splits long JSON across rows → wrote a re-assembler (251 of 277 successful responses recovered, 237 distinct buyers). WhatsApp chatbot `intent` tells seller-support questions apart from the seller acting as a buyer. |
| 2. Listen to the calls | Read real VANI transcripts | Sellers say *“Madam hum mil chuke hain aapke executive se”*, *“aap roz same baat kar rahe ho”*, *“already meri paid membership chaalu hai”* — facts that were already in other channels. This became the core metric. |
| 3. Design the file | Fixed sections + token budget + front-matter | “Before you speak” guardrails first, “Suggested opening” last; hard cap 450 tokens; drop least-important bullets first. |
| 4. Event store + engine | SQLite event log, per-section builders with channel dependencies | Only affected sections are recomputed per event; cached sections store absolute timestamps so they never go stale. |
| 5. Point-in-time correctness | Every build reads only events before `as_of` | Lets us rebuild the exact memory VANI *would* have had 1 minute before each of 9,657 real calls — no leakage. |
| 6. Signals from data | Wrong-number, repeat-call fatigue, executive contact, open WhatsApp question, callback request, unread enquiries, buyer awaiting reply, call language | Each validated against real outcomes (meeting rate 1.7%–19.3% by flag vs 11.2% baseline). |
| 7. Lookback window | Measured time from a seller's last touch to each VANI call | 14-day conversation tier (64.5% of last touches), 30/90-day pulse (90 d covers 98% of all touches). |
| 8. Voice + WhatsApp agents | Sarvam-105B (LLM), Bulbul v3 (TTS), Saaras v4 codemix (STT); offline policy fallback | The opener is generated from the file; the call language follows evidence (e.g. Gujarati); every call writes its summary back. |
| 9. Async AI polish | Background Sarvam-105B pass rewrites threads + opener | Bot never waits: deterministic file in ms, AI-polished version a second later. |
| 10. Evaluation | `python -m gcx eval` | Freshness p50 6 ms / p95 27 ms on 3,000 replayed events; incremental = full rebuild (100%); 26.7% of real calls started cold despite fresh cross-channel activity; +18.9% meetings estimate from memory-based call routing. |
| 11. Demo UI | 3-pane web app (WhatsApp · live file · voice call) | Changed lines glow on every update; memory on/off toggle shows cold vs warm opening side by side. |
| 12. Portability | `run.sh` / `run.bat` / Docker, bundled fonts, 3 MB demo slice, offline mode | Runs on any laptop with Python 3.10+, with or without internet / API keys. |
| 13. Regression pass on the official files | Re-ran everything on the untouched hackathon download; scanned all 5,237 generated files for artefacts; 47-check live API script (`scripts/api_regression.py`); UI click-through | Found and fixed: the official buyer file name (`…_Buyer Side.csv`, with a space) was not detected → 0 buyer files; URL-encoded search terms (`sticky%20mats`) splitting one interest into two; “last active” ignoring a newer posted requirement; empty `“”` quotes and `Account: –`; case-duplicate products. Added app/web chat as real channels (deck: “voice, WhatsApp, chat and app”). Every fix has a regression test. |
| 14. Live Sarvam pass | Real Bulbul / Saaras / Sarvam-105B calls: latency per step, Gujarati, rate limits, LLM-judged resume benchmark | Opener took 5.8–7.7 s → pre-generated in the background (~35 ms). Reply audio 2–6 s → head phrase + rest in parallel (first audio ~2.4 s). Hit **429 rate limits** (Starter: bulbul:v3 30/min, 105b 40/min) → local per-minute budget, max 2 TTS requests per reply, optional work skipped when quota is low. Fixed: Gujarati opener used the masculine form for Ananya; the WhatsApp bot answered as if on a phone call; the bot guessed “kal” for a message sent minutes ago; a “catalog update karna hai” request was not seen as an open thread. The first LLM-judged benchmark was wrong twice: the judge invented fact names, and 100 of 120 rows had silently fallen back to rules under 429s. Both fixed (strict judge, batch mode that waits for quota, honest engine labels). |

## Tools used

| Area | Tool |
|---|---|
| Voice | **Sarvam AI** — Bulbul v3 (text-to-speech, hi-IN / gu-IN …), Saaras v4 (speech-to-text, `codemix` mode), Sarvam-105B (chat completions), Voice Agents (on_start / on_end HTTPS tools) |
| Backend | Python 3, FastAPI, Uvicorn, SQLite (WAL), pandas, requests, PyYAML |
| Frontend | Vanilla HTML/CSS/JS (no build step), Server-Sent Events, MediaRecorder, Web Speech API fallback |
| Quality | pytest (16 tests incl. API end-to-end, point-in-time leakage, thread resolution, official-file detection, app/web chat), live API regression script (47 checks), pyflakes, Playwright (UI screenshots) |
| AI pair-programming | Claude (Anthropic) for data exploration, code, evaluation design and docs — every number was produced by code in this repo |
| Packaging | venv scripts for macOS/Linux/Windows, Dockerfile + docker-compose |

## Reproduce every number
```bash
python -m gcx setup --data <full data folder>
python -m gcx eval                                          # compactness, freshness, consistency, impact
python scripts/personalised_trial.py --persona <dir> --btc <dir>   # personalised-script trial
```
