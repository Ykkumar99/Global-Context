# Global Context — evaluation report
_Generated 2026-10-09 14:53 on dataset `data/raw`_

## Compactness — seller.md (5,000 files)
- Median **269 tokens** (p95 386, hard cap 450)
- Raw source data per user: median 1,112 tokens → **4.1× compression**
- Schema-valid files: 100.0% · opening references a specific recent event: 26.5% (all others: name + category + city)
- Section coverage: Suggested opening (Hinglish) 100.0%, Engagement history 99.6%, Last conversations 89.8%, Business pulse (30d | 90d) 81.1%, Before you speak 56.2%, Open threads 25.2%

## Compactness — buyer.md (237 files)
- Median **173 tokens** (p95 327, hard cap 450)
- Raw source data per user: median 1,809 tokens → **12.3× compression**
- Schema-valid files: 100.0% · opening references a specific recent event: 84.0% (all others: name + category + city)
- Section coverage: Suggested opening (Hinglish) 100.0%, Engagement signals 99.6%, What they are looking for 84.8%, Before you speak 40.5%, Last conversations 8.9%

## Privacy (cross-party)
- 5,237 files checked against 22,090 known buyer names: **0 quote another party's name**, **0 contain a phone number or email**

## Freshness — replay of the last 3 days (3,000 real events, 397 sellers)
- Event → updated file: **p50 5.08 ms, p95 21.28 ms**, p99 34.22 ms
- Incremental vs full rebuild (event-driven sections identical): **100.0%**
- Full rebuild of 5,000 sellers: 13.76 s (2.75 ms/seller)

## Conversations resumed without re-asking — 60 WhatsApp → voice scenarios (rules)
| | Memory on | Memory off (today) |
|---|---|---|
| Call picks up the WhatsApp thread | **100.0%** | 0.0% |
| Calls where the bot re-asks a given fact | **0.0%** | 20.0% |
| Given facts re-asked | **0.0%** | 10.0% |

## Business impact — 9,657 real VANI calls, context rebuilt as of 1 min before each call
- **26.7%** of calls happened within 7 days of the seller's activity on another channel — and today all of them started cold
- 34.5% had an actionable memory flag (open thread, executive contact, wrong number, repeated calls)
- 33.0% could open with a specific, personal reference
- Skipping/rescheduling calls memory flags as fatigued or wrong-number (19.5% of dials, 46 meetings) and redeploying that capacity: **+18.9% meetings at the same call volume** (estimate)
- Seller pushback like “already met / already told you / wrong number”: 31 of 455 transcripts; **45.2% predictable from memory**

| Memory flag at call time | Calls | Meeting fixed | Not interested | p (meeting vs rest) |
|---|---|---|---|---|
| ALL | 9,657 | 11.2% | 42.2% | – |
| cross_channel_activity_7d | 2,575 | 10.0% | 41.7% | 0.0314 |
| SUPPRESS: fatigue or wrong number | 1,881 | 2.4% | 44.7% | 0.0 |
| called_2plus_times_this_week | 1,803 | 2.4% | 44.9% | 0.0 |
| open_thread:callback | 986 | 7.3% | 43.8% | 0.0 |
| PRIORITISE: seller-initiated thread | 498 | 18.5% | 25.9% | 0.0 |
| open_thread:unread | 279 | 7.9% | 47.3% | 0.0777 |
| open_thread:wa_callback | 271 | 17.0% | 15.5% | 0.0021 |
| wrong_number_on_recent_call | 239 | 1.7% | 43.9% | 0.0 |
| open_thread:buyer_waiting | 204 | 2.9% | 42.6% | 0.0002 |
| met_or_in_touch_with_executive | 186 | 7.5% | 50.5% | 0.1118 |
| open_thread:meeting | 166 | 19.3% | 31.9% | 0.0008 |
| open_thread:wa_question | 87 | 18.4% | 44.8% | 0.0315 |

**Pushback examples (seller's words) and what memory already knew:**

- “Kya baat ho gayi batao toh?” → memory: SUPPRESS: fatigue or wrong number, called_2plus_times_this_week, cross_channel_activity_7d (Call Later / Busy)
- “Mam kal baat ho gayi thi already aap roz same baat kar rahe ho call karke. Mujhe rahega to main saamne se aapko contact kar lunga.” → memory: open_thread:callback (Call Later / Busy)
- “Mera already hai aapke yahan registered, Surya Sales ke naam se ma'am.” → memory: — (Not Interested)
- “Nahi madam maine bola tha mujhe koi ye nahi interest nahi hai, mujhe aage ye nahi karna hai madam, aise bola tha maine. Theek hai?” → memory: — (General (talked))
- “Abhi kuch hafte pehle ek jan mil ke gaye hain yahan se.” → memory: — (General (talked))
- “Maine... mujhe nahi chahiye. Ek baar maine open kar diya toh uska matlab nahi ki aap yahan se sab call karte baithe baar baar please. Thank ” → memory: — (Not Interested)
