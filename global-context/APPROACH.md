# Approach note — sources, lookback window, refresh logic

## 1. What the file is for

The bot has ~2 seconds before it speaks. It needs a **short, structured, current** brief that answers:
*Who is this? What happened recently on any channel? Is anything still open? Is there a reason to be careful?
How should I open?* — and nothing else. Everything in `seller.md` / `buyer.md` is chosen against that test.

## 2. Sources used

### Seller (`seller.md`) — the 11 Global Context files, normalised into one event stream

| Source file | Channel in the store | Used for |
|---|---|---|
| `gc_seller_profile.csv` | profile | header (business, categories, account, KYC), past objections/questions, DNC & frustration flags |
| `gc_enquiries_received.csv` | `enquiry` | unread enquiries (open thread), 30/90-day pulse, top products, buyer cities |
| `gc_enquiry_messages.csv` | `enquiry_reply` | buyer waiting for the seller's reply (open thread), seller's last reply |
| `gc_buyer_calls_received.csv` | `buyer_call` | pulse (calls / answer rate), best time to reach |
| `gc_buyleads_bought.csv` | `buylead` | pulse (leads, credits, keywords), opener for lead buyers |
| `gc_whatsapp_messages.csv` | `wa_msg` | WhatsApp reach & read rate, seller replies |
| `gc_whatsapp_chatbot_conversations.csv` | `wa_chat` | questions typed by the seller (open thread → opener), callback requests, products they source as a buyer |
| `gc_buyer_call_extractions.csv` | `pns_extract` | languages spoken (→ call language), products discussed |
| `gc_bot_calls.csv` + `gc_bot_call_turns.csv` | `bot_call` | last conversations, call-later / meeting-fixed threads, wrong-number and “already met executive” detection, repeat-call fatigue, engagement history |
| `gc_executive_calls.csv` | `exec_call` | “spoke with an executive N days ago” guardrail, last conversations |
| live demo / production events | `wa_chat`, `voice_call` | written back by the WhatsApp bot and every voice call |

### Buyer (`buyer.md`) — IndiaMART's existing `getContext` API

The provided buyer CSV is a log export of real `getContext` responses (7–33 KB of nested JSON each, rows split
across lines by the export — `ingest.py` stitches them back). We distil: identity & account (`kycdetails`),
what they're pursuing (`BUYER_ACTIVITY` weighted: call/BL > enquiry > search > view), last enquiry & live
requirements (`LAST_ENQUIRY`, `LAST_LEAD`, `BLdetails`), sellers they just spoke to / missed / who responded
(parsed from `LAST_WA9696_CHAT`/`LAST_WA8181_CHAT` templates), and complaints (`ticketsdetails`).
In production `gcx.buyer_sections.build_buyer_md_parts()` runs directly on the live API response.

### Privacy
Phone numbers and emails are masked in every file and stripped from demo data; no contact details ever reach the
prompt. Only the fields above are used.

## 3. Lookback window — tiered, chosen from the data

We measured, for all 9,657 real VANI calls, how long before the call the seller's previous touch on any channel was:

| Last touch within | 1 d | 3 d | 7 d | **14 d** | 30 d | 60 d | **90 d** | 180 d |
|---|---|---|---|---|---|---|---|---|
| Share of calls (cumulative) | 36.4% | 49.4% | 56.5% | **64.5%** | 73.3% | 81.7% | **85.3%** | 87.4% |

So the file uses three tiers:

| Tier | Window | Content | Why |
|---|---|---|---|
| Conversation detail | **14 days** (threads stay open 21 d) | individual conversations, open threads, guardrails | covers ~2/3 of calls' last touch while staying specific; older conversations rarely matter word-for-word |
| Pulse | **30 / 90 days** | counts & rates (enquiries, buyer calls, leads, WhatsApp) | 90 d captures 98% of all touches that exist (85.3 of 87.4 points) |
| Lifetime | since Apr 2026 / profile | business, categories, KYC, objections, engagement history | stable facts |

All windows are config (`config.yaml → lookback`) and every file is built *point-in-time*: only events before
`as_of` are read, which is also what makes the evaluation leak-free.

## 4. Keeping it short and structured

- Fixed sections, always in the same order: header → *Before you speak* → *Open threads* → *Last conversations* →
  *Business pulse* → *Engagement history* → *Suggested opening*.
- Hard token budget (450). If exceeded, bullets are dropped from the least important sections first
  (engagement → pulse → recent), never the header, guardrails or opener.
- YAML front-matter (`glid, role, as_of, version, llm_enriched, sources`) makes files machine-readable and auditable.

**Why ~450 tokens:** the median file is 269 tokens — under 1% of the 32K context of `sarvam-105b-conversations`, so
it adds no noticeable latency to the first spoken word, yet it holds up to four items per section, which covered 98%
of sellers without truncation. Larger files mostly added old pulse counts the bot never used in an opening.

## 5. Refresh logic

1. **Event arrives** (`POST /api/events`, or a Kafka consumer in production) → appended to the store.
2. **Only affected sections are recomputed** (`SECTION_DEPS` maps channel → sections; e.g. a WhatsApp message touches
   *Open threads*, *Last conversations*, *Pulse* and the opener, not the header). Cached sections hold absolute
   timestamps; “3d ago” is resolved at render time, so cached text never goes stale.
3. **File re-rendered and written** → measured **p50 6 ms / p95 27 ms** on a replay of 3,000 real events.
4. **AI polish (optional, async):** Sarvam-105B rewrites *Open threads* and the opener from the fresh file
   (~1–3 s). Until it returns, the deterministic version is served — the bot never waits, never sees stale facts.
5. **Windowed counts** (7/14/30/90-day) drift with time, so a seller's next event triggers a full refresh if the last
   one is older than 60 minutes; a nightly sweep rebuilds everything (5,000 sellers in ~13 s).
6. **Proof:** after the replay, incrementally maintained files are **100% identical** to a from-scratch rebuild.

## 6. Cold start, privacy and other channels

- **Cold start (no history anywhere):** `/context/{glid}.md` returns a clean file marked `cold_start: true` with a
  generic, honest opener ("Aap IndiaMART par kuch kharidna chahte hain ya apna business badhana chahte hain?") and a
  guardrail not to claim any knowledge. The first event from that GLID creates a profile, so a user who writes on
  WhatsApp is already "warm" on the next call. Sellers with a profile but little activity get a name + category +
  city opener.
- **Cross-party privacy:** seller files never quote a buyer's personal name. Counterpart names are harvested from
  enquiry and reply subjects and scrubbed (with salutation patterns) from every quoted text; buyers are referred to
  only by city or product. Phone numbers and emails are masked everywhere; internal staff names are not included.
  Both agent prompts carry an explicit rule never to reveal another party's name, number, messages or prices.
  Checked automatically: 0 of 5,237 files leak a counterpart name.
- **Partial or conflicting data:** every line comes from one dated event; missing fields drop out instead of being
  guessed; profile aggregates that conflict with newer events lose to the events (point-in-time builds).
- **App and web chat (implemented):** `app_chat` and `web_chat` are first-class channels next to `wa_chat`
  (`seller_sections.CHAT_CHANNELS`). They feed *Open threads*, *Last conversations* and the opener with their own label
  ("App chat 2 min ago: …" → "Aapne IndiaMART app par … poochha tha"), and buyer files list them under *Last
  conversations*. Send them with `POST /api/chat {glid, text, channel}` or `POST /api/events`; the demo's chat pane
  has a WhatsApp / App chat / Web chat switch. The current VANI bot prompt is integrated by
  prepending its instructions to `VOICE_SYS` and keeping the CONTEXT block unchanged.

## 7. Measuring "resumed without re-asking"

`python -m gcx resume-eval`: 60 scenarios (12 sellers × 5 WhatsApp messages: a requirement with product, quantity
and city; a pricing question; a callback time; a location preference; a catalogue request). After each message the
voice call starts twice — memory on and memory off — and we check the bot's opening and first reply for (a) a
reference to the WhatsApp thread and (b) any question asking for a fact the user already gave. Rule-based detectors
run offline; with a Sarvam key the bot turns come from Sarvam-105B and an LLM judge re-checks every verdict.

## 8. How the bot uses it

- **Voice (Sarvam):** `seller.md` goes into the system prompt; the opener comes from *Suggested opening*; the call
  language comes from evidence in past calls (e.g. Gujarati → `gu-IN` Bulbul voice); at hang-up the call is
  summarised and written back as a `voice_call` event.
- **WhatsApp:** same file, same write-back — so the next channel resumes without re-asking.
- **Sarvam Voice Agent:** `on_start` HTTPS tool → `GET /sarvam/context`, `on_end` → `POST /sarvam/call-ended`.
- **Beyond the bot:** the same file is a 20-second pre-call brief for sales executives, and the flags (fatigue,
  wrong number, seller-initiated threads) feed dialer prioritisation.
