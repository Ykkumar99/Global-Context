# Regression & requirements report — Problem 2: Global Context

_9 Oct 2026 · tested on the official hackathon download (`Aids to solve Problems` zip) and the deck `Voice_AI_Hackathon_2.0_Deck_Revised - Final.pptx` (slides 7–9, 23, 25)._

## Result

| Suite | Result |
|---|---|
| Unit tests (`python -m pytest -q`) | **21 / 21 pass** (was 11; 10 new regression tests) |
| Live API regression (`python scripts/api_regression.py`) | **47 / 47 pass**: every route, the WhatsApp → voice → WhatsApp resume, app/web chat, buyer, cold start, bad input, Sarvam hooks |
| Full official dataset | 5,000 `seller.md` + **237** `buyer.md`, 100% schema-valid, 0 artefacts across all 5,237 files |
| Static checks | pyflakes clean · `node --check web/app.js` OK · 0 server errors in logs |
| UI click-through (browser) | WhatsApp msg → file updated in 8 ms → call opens with that exact question → End & save written back in 19 ms → App chat → next call opens from app chat |

## Bugs found and fixed

| # | Severity | Problem | Fix | Guarded by |
|---|---|---|---|---|
| 1 | **Critical** | The official buyer file is named `Global_Context_Problem_Statement_Buyer Side.csv` (with a **space**). The loader only matched `buyer_side`, so on the real download **0 buyer.md files** were built. The README's "237 buyers" came only from the pre-sliced demo data. | Name matching now treats space, hyphen and underscore as the same. The newest snapshot per buyer is picked by parsed timestamp (Kibana format `Oct 1, 2026 @ 10:26`) instead of file order. | `test_official_buyer_export_filename_is_detected` |
| 2 | High | Search keywords arrive URL-encoded (`sticky%20mats`, `tensile%20structures`) in 21 of 237 buyers. They showed up in files and in the spoken opener, and split one interest into two lines. | URL-decoding of keywords, categories, last enquiry and posted-requirement titles. | `test_buyer_file_decodes_keywords_and_uses_newest_touch` |
| 3 | High | Deck asks to resume across "voice, WhatsApp, **chat and app**". `app_chat` / `web_chat` events were accepted by the API but **never appeared in the file** (APPROACH.md only described them). | Made them first-class channels (`CHAT_CHANNELS`). They feed open threads, last conversations, buyer files and the opener, each with its own label ("Aapne IndiaMART app par…"). Added `POST /api/chat {channel}` and a WhatsApp / App chat / Web chat switch in the UI. | `test_app_and_web_chat_resume_like_whatsapp` + 4 API checks |
| 4 | Medium | buyer.md said "last active 13d ago" next to "requirement posted 01 Oct", because it only looked at the activity log. | Last active is now the newest touch from any source. Buyer "Engagement signals" coverage went from 30.8% to 99.6%. | same test |
| 5 | Medium | Empty quotes `Replied to 1 buyer enquiry: “”` and `Last enquiry: “”`; placeholders `**Account:** – ·  · KYC`. | Empty fields are dropped instead of rendered. | `test_no_empty_quotes_or_placeholders_in_any_file` |
| 6 | Low | Case duplicates in the pulse line (`top: maid service, Maid Service`). | Case variants are merged when counting the top products, cities and keywords. | `test_seller_pulse_merges_case_variants` |
| 7 | Low | `eval_report.md` always said "dataset `data/demo`" even when run on the full data. | The ingest folder is now recorded in the store and used in the report. | — |
| 8 | Low | "End & save" before the user spoke did nothing visibly, which looks broken in a demo. | It now shows "Call ended before the user said anything — nothing new to save." | UI check |
| 9 | Low | The browser kept an old `app.js` after updates (seen during testing). | `Cache-Control: no-cache` on UI files. | UI check |
| 10 | Low | Sarvam `on_end` could send the transcript as a JSON-encoded list string. | Parsed when it looks like JSON. | — |
| 11 | Low | The opener copied the user's capitalisation mid-sentence ("…app par Kal subah 11 baje…"). | The time phrase is lower-cased in the opener. | — |

Docs updated to match the measured numbers. README, APPROACH.md and skills.md now give buyer median 173 tokens (12× compression) and freshness p50 6 ms / p95 27 ms. The lift claim now also states the non-significant answered-call result.

## Deck requirements vs evidence

### What you'll build (slide 8)

| Requirement | Status | Evidence |
|---|---|---|
| Context layer keyed to GLID, sources participants choose | ✅ | All 11 seller CSVs + buyer `getContext` export → one SQLite event store keyed by GLID (APPROACH §2) |
| buyer.md: enquiries, categories searched, sellers contacted, KYC, past conversations, engagement signals | ✅ (fixed #1, #2, #4) | 237 files from the official export; every field present where the data has it |
| seller.md: leads received, responses and call outcomes, categories/products, past conversations, engagement signals | ✅ | 5,000 files; section coverage in `outputs/eval_full_dataset/eval_report.md` |
| Bot loads the file before each call/chat, personalised opener, resumes across voice, WhatsApp, chat and app | ✅ (fixed #3) | `/api/call/start`, `/api/chat`, `/sarvam/context`; verified in UI and API suite |
| Short, structured, always up to date | ✅ | Median 269 / 173 tokens, hard cap 450; incremental refresh 100% identical to a full rebuild |
| Right lookback window | ✅ | Tiered 14 d / 30–90 d / lifetime, chosen from the data (APPROACH §3) |

### Expected outputs (slide 9)

| Output | Status | Where |
|---|---|---|
| Generated buyer.md and seller.md for sample GLIDs | ✅ | `outputs/seller_md/` (67), `outputs/buyer_md/` (237) |
| Demo: a conversation that resumes across two channels | ✅ | UI steps 1–6 in README; `DEMO_SCRIPT.md` |
| Note on sources, lookback window and refresh logic | ✅ | `APPROACH.md` |

### Success metrics (slide 9), measured on the full official data

| Metric | Result |
|---|---|
| Freshness | Event → updated file **p50 5.8 ms, p95 27 ms** (3,000 replayed real events) |
| Compactness and structure | 100% schema-valid; median 269 tokens (seller), 173 (buyer); 4.1× / 12.3× compression |
| Conversations resumed without re-asking | Memory on: **100%** pick up the thread, **0%** re-ask · memory off: 0% / 20% |
| Lift from the personalised opening | IndiaMART's own trial, re-run here: **+29.9% meetings per dial (p = 0.031)**; +22.1% per answered call (p = 0.09, not significant) |
| Reusability beyond the bot | `/brief/{glid}` executive brief, `/api/segments` campaign segments, plain `GET /context/{glid}.md` |

## Live Sarvam pass (key added)

All of Sarvam-105B, Bulbul v3 and Saaras v4 work. The live API suite passes **47 / 47 in Sarvam mode with 0 rate-limit hits**; unit tests are **18 / 18** and stay offline even with a key in `.env`.

| Measure | Before | After |
|---|---|---|
| "Start call" → opening line + audio ready | 5.8–7.7 s | **~35 ms** (pre-generated when the user is opened or their file changes) |
| User stops speaking → Payal's voice starts | 4–7 s | **~2.4 s median** (head phrase + rest synthesised in parallel, head plays first) |
| Sarvam-105B reply / Saaras STT | 0.7–1.0 s / 0.6–0.8 s | unchanged |
| Resume benchmark, real LLM + LLM judge, 120 calls per run | judge invented facts; 100 / 120 rows had silently fallen back to rules | **memory on: 96.7% pick up the thread, 1.7–5.0% re-ask** · memory off: 20–32% / 20–23% (2 clean runs; `outputs/eval_full_dataset/resume_eval_sarvam.json`) |

Fixed in this pass:

| # | Problem | Fix |
|---|---|---|
| 12 | **429 rate limits.** The Starter plan allows bulbul:v3 30/min and sarvam-105b 40/min; parallel chunks and pre-warming went over. A 429 also fell through all 3 TTS request variants, burning 3 requests. | Local per-minute budget (35 / 27 / 55, `config.yaml`); max 2 TTS requests per reply; stop immediately on a 429; optional AI polish and pre-warm skipped when quota is low |
| 13 | Gujarati opener used the masculine form for Payal ("vaat kari *rahyo* chhu") | Translator told Payal is a woman → "*rahi* chhu" |
| 14 | The WhatsApp bot replied as if on a phone call ("…call kiya hai, do minute milenge?") | Chat prompt: text chat only, never reuse the voice opener |
| 15 | The bot said "aapne **kal** WhatsApp par…" for a message sent minutes ago (the prompt's example said "kal") | Prompt keeps timings exactly as in the file |
| 16 | After "haan boliye" the bot switched to a different or older thread | Rule: stay on the topic just raised; don't bring up older messages |
| 17 | "Mera catalog update karna hai…" was not recognised as an open request, so the call opened with an older message | Request detection widened (catalog, update, add, karna hai…). On the full data, open WhatsApp question calls now show **18.4% meetings vs 11.2%, p = 0.03** |
| 18 | The resume benchmark's judge counted invented facts and meeting-slot questions as re-asks; mixed offline rows were labelled "sarvam+judge" | Judge limited to the given facts; batch mode waits for quota; engine mix reported honestly |
| 19 | Unit tests silently called the real Sarvam API once `.env` had a key | Tests pin `SARVAM_API_KEY=""` |

| 20 | **Privacy (found on the live agent):** the AI-polish step sent raw replies ("Hi Panini, …") to the LLM, which then wrote the buyer's name into *Open threads* | Counterpart names scrubbed from the LLM input **and** its output; the seller's own company words are kept. Test with a deliberately leaky fake LLM |
| 21 | An empty Sarvam `on_end` call (tool test or unanswered call) wrote a blank "User said: ''" call into memory | Skipped when the transcript has no user speech |
| 22 | Exposing the server through a public tunnel would open every route, including ones that spend Sarvam credits | Requests through the tunnel can only reach `/sarvam/*` with the secret `GCX_TUNNEL_TOKEN` (header `x-gcx-token`); everything else answers 403 |

| 23 | **"Hold to talk" failed with Sarvam:** the browser records WebM/Opus, which Saaras rejects (400 *Invalid file type*). Only WAV had been tested before | Browser converts the recording to 16 kHz mono WAV before upload (also 3× smaller); server strips `;codecs=` from the type. Verified: real MediaRecorder WebM → WAV → Saaras heard "हाँ बोलिए, कल शाम चार बजे executive से बात करा दो।" (STT 0.95 s, turn 2.1 s) |
| 24 | User said "**kal** shaam 4 baje", the bot confirmed "**aaj** shaam 4 baje" | Rule: repeat the user's exact day/time words when confirming (also in the Samvaad prompt); re-tested twice → "kal" kept |
| 25 | **Caller spoke English, Payal kept answering in Hinglish.** The server mapped Saaras' `en-IN` to `hi-IN` on purpose, and the prompt said "always Hinglish" | Every turn detects the caller's language (Indic script, or Hindi words vs plain English in Roman text, with Saaras' code as a hint). The prompt leads with that language, the reply voice uses it, and if the model still copies earlier Hinglish one rewrite call fixes it. Live test: English → English, Hinglish → Hinglish, Gujarati → ગુજરાતી, with the meeting time kept ("4:30 PM tomorrow") |
| 26 | **Push-to-talk felt unlike a phone call** (user request) | Hands-free call: the mic stays open for the whole call; an in-browser voice-activity detector (adaptive noise floor, 1 s pre-roll, 0.75 s end-of-turn) sends each turn to Saaras as 16 kHz WAV; **barge-in** stops Payal's audio the moment the caller talks and drops her stale reply. New call screen: live status, timer, mic level, Mute, End call |
| 27 | First barge-in test took **1.9 s** and cut "Ruko ruko" | The caller's own first syllables were raising the noise floor. Fixed with a min-tracking floor and a leaky onset counter → **0.59 s** (incl. 0.34 s of leading silence in the test clip), first words kept |
| 28 | Replies ignored the caller's mood; Payal sounded scripted and once promised an executive time from old notes | Per-turn mood (frustrated / busy / confused / positive, Hinglish + English + Devanagari cues) steers tone, length and Bulbul pace; prompt for natural, non-repetitive phone speech; rule not to promise times from old notes. Live: "roz roz call karke pareshan…" → 😤 → "Mujhe maaf kijiye, aapki pareshaani samajh mein aa rahi hai… baad mein baat kar lenge" |
| 29 | Demo call still less fluent than Sarvam's own agent (barge-in on echo, "sunai nahi diya" loops) | Browser calls now run on **Sarvam's real-time Samvaad engine** with the Payal agent, with memory passed in when the call starts. Three blockers fixed: the socket returned a bare **403** because `user_identifier_type` was `glid` (allowed: phone_number, email, custom, unknown) → `custom`; the agent had **no committed version** → v1 committed; a blocked mic left the call stuck on "connecting" → mic checked first, with a clear fallback to the built-in loop |
| 30 | Live Samvaad calls (simulated caller over the same socket, 2 calls / 7 turns) | Opens from memory ("aapne 11 baje callback ke liye kaha tha"); reply starts **0.1–0.6 s** after the caller stops; barge-in fires on every caller turn; Hindi→English on request→Hindi; angry caller → apology + callback ask; "Gujarati ma vaat karo" → Gujarati; books the callback time and hangs up itself |
| 31 | Samvaad calls saved to memory only via the agent's tool, which needs the public tunnel | The browser saves the transcript itself on hang-up (including when the agent hangs up); `/sarvam/call-ended` skips the duplicate for 180 s. Tested: save → v+1, tool's duplicate → skipped |
| 32 | **After a server restart, calls from earlier sessions dropped out of memory** | The demo clock restarted at the last *dataset* event, so earlier live calls looked like future events and rebuilds skipped them. The clock now resumes after the latest event of any kind |
| 33 | Agent tools pointed at `localhost:8000` (unreachable from Sarvam) and the agent introduced itself as "Shikha" | Tools point at the current tunnel (Load Context test: Success), name back to **Payal**, committed as **v2** (`config.yaml` app_version 2). Live: "aapka naam?" → "mera naam Payal hai"; on hang-up the agent's save_call tool wrote the call into seller.md through the tunnel |

Hands-free engine tested in the browser by feeding real Bulbul speech into it frame by frame at real-time pace
(the preview pane blocks the microphone): Listening → speaking → thinking → reply 0.7 s after the caller stops;
barge-in 0.59 s; call saved to memory on End call (50 ms). Live API suite 47/47 afterwards.

**Live Sarvam Voice Agent** (Samvaad, now `Payal---Glo-ed092fb2-9b6f` in Vishwas's Organisation; first built and tested as `Payal---Glo-b7f05376-3920`): `load_context` (on start) and `save_call` (on end) both return **Success** from Sarvam through the tunnel. In a chat test the agent greeted with the memory line ("…Aapne abhi WhatsApp par Premium plan ka charges aur leads ke baare mein poocha tha…") and continued that thread. Sarvam's chat test mode does not fire `on_end`; the write-back is verified with the tool test and needs one voice call for the end-to-end proof.

Still noisy: the LLM judge itself (also sarvam-105b) occasionally marks a confirmation ("aapne 200 kg … poocha tha, kya abhi bhi wahi order?") as a re-ask, so the 1.7–5.0% is an upper bound.

## Still for the team to do

1. **Agent ID / live link on the Sarvam platform.** Needs your login on dashboard.sarvam.ai plus a public HTTPS tunnel to this laptop (`sarvam_agent/README.md`).
2. **Demo video (5–7 min)** and **team name / member details.**
3. The API key was shared in a chat. Rotate it on dashboard.sarvam.ai after the hackathon.

## How to re-run everything

```bash
python -m pytest -q                                   # unit + regression tests
python -m gcx serve                                   # then, in another terminal:
python scripts/api_regression.py                      # 47 live API checks
python -m gcx setup --data data/raw && python -m gcx eval   # full official data
```

`outputs_full/` holds the 5,237 files built from the full real data during this pass. It is git-ignored and docker-ignored, because the data must stay on IndiaMART machines.
