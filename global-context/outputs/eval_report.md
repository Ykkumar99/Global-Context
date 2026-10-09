# Global Context — evaluation report
_Generated 2026-10-09 12:02 on dataset `D:/Downloads/global-context-P2-solution/global-context/data/demo`_

## Compactness — seller.md (67 files)
- Median **275 tokens** (p95 438, hard cap 450)
- Raw source data per user: median 1,131 tokens → **3.9× compression**
- Schema-valid files: 100.0% · opening references a specific recent event: 29.9% (all others: name + category + city)
- Section coverage: Suggested opening (Hinglish) 100.0%, Engagement history 97.0%, Last conversations 89.6%, Business pulse (30d | 90d) 85.1%, Before you speak 61.2%, Open threads 25.4%

## Compactness — buyer.md (237 files)
- Median **173 tokens** (p95 327, hard cap 450)
- Raw source data per user: median 1,790 tokens → **12.3× compression**
- Schema-valid files: 100.0% · opening references a specific recent event: 84.0% (all others: name + category + city)
- Section coverage: Suggested opening (Hinglish) 100.0%, Engagement signals 99.6%, What they are looking for 84.8%, Before you speak 40.5%, Last conversations 8.9%

## Privacy (cross-party)
- 304 files checked against 772 known buyer names: **0 quote another party's name**, **0 contain a phone number or email**

## Freshness — replay of the last 3 days (184 real events, 23 sellers)
- Event → updated file: **p50 3.47 ms, p95 11.4 ms**, p99 15.8 ms
- Incremental vs full rebuild (event-driven sections identical): **100.0%**
- Full rebuild of 67 sellers: 0.14 s (2.16 ms/seller)

## Conversations resumed without re-asking — 60 WhatsApp → voice scenarios (rules)
| | Memory on | Memory off (today) |
|---|---|---|
| Call picks up the WhatsApp thread | **100.0%** | 3.3% |
| Calls where the bot re-asks a given fact | **0.0%** | 20.0% |
| Given facts re-asked | **0.0%** | 10.0% |

## Business impact — 151 real VANI calls, context rebuilt as of 1 min before each call
- **38.4%** of calls happened within 7 days of the seller's activity on another channel — and today all of them started cold
- 43.7% had an actionable memory flag (open thread, executive contact, wrong number, repeated calls)
- 41.7% could open with a specific, personal reference
- Skipping/rescheduling calls memory flags as fatigued or wrong-number (26.5% of dials, 1 meetings) and redeploying that capacity: **+28.5% meetings at the same call volume** (estimate)
- Seller pushback like “already met / already told you / wrong number”: 1 of 10 transcripts; **0.0% predictable from memory**

| Memory flag at call time | Calls | Meeting fixed | Not interested | p (meeting vs rest) |
|---|---|---|---|---|
| ALL | 151 | 11.9% | 41.1% | – |
| cross_channel_activity_7d | 58 | 6.9% | 41.4% | 0.1324 |
| SUPPRESS: fatigue or wrong number | 40 | 2.5% | 42.5% | 0.032 |
| called_2plus_times_this_week | 34 | 2.9% | 47.1% | 0.0664 |
| open_thread:unread | 20 | 0.0% | 40.0% | 0.0773 |
| open_thread:callback | 15 | 6.7% | 33.3% | 0.5082 |
| open_thread:buyer_waiting | 15 | 6.7% | 26.7% | 0.5082 |
| wrong_number_on_recent_call | 12 | 0.0% | 16.7% | 0.1841 |
| PRIORITISE: seller-initiated thread | 11 | 18.2% | 27.3% | 0.5057 |
| open_thread:wa_callback | 9 | 22.2% | 22.2% | 0.3253 |
| open_thread:meeting | 1 | 0.0% | 0.0% | 0.712 |
| open_thread:wa_question | 1 | 0.0% | 100.0% | 0.712 |

**Pushback examples (seller's words) and what memory already knew:**

- “Ma'am, already meri paid membership chaalu hai. Uspe hi kuch lead nahi mil rahi hai, uspe hi kuch kaam nahi ho paa raha hai.” → memory: — (Meeting Fixed)
