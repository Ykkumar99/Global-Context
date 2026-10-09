"""Deterministic section builders for seller.md.

Each builder reads only the channels it depends on (see SECTION_DEPS) for one
GLID, at a point in time ``now`` (no future data can leak in), and returns a
list of markdown lines. The refresh engine recomputes only the sections whose
channels received a new event.
"""
from __future__ import annotations

import re
from collections import Counter
from datetime import datetime, timedelta

from .textutil import clean, counterpart_names, fmt_date, hour_band, pct, rel, rel_hi, scrub_people

# typed-chat channels: WhatsApp plus the IndiaMART app and web chat, handled identically
CHAT_CHANNELS = ("wa_chat", "app_chat", "web_chat")
CHAT_LABEL = {"wa_chat": "WhatsApp", "app_chat": "App chat", "web_chat": "Web chat"}
CHAT_LABEL_HI = {"wa_chat": "WhatsApp par", "app_chat": "IndiaMART app par", "web_chat": "website chat par"}

# section -> channels it reads. "profile" = the profile snapshot.
SECTION_DEPS: dict[str, set[str]] = {
    "header": {"profile"},
    "guardrails": {"profile", "bot_call", "exec_call", "buyer_call", "pns_extract", "voice_call"},
    "threads": {*CHAT_CHANNELS, "bot_call", "enquiry", "enquiry_reply", "exec_call", "voice_call"},
    "recent": {"bot_call", "exec_call", *CHAT_CHANNELS, "enquiry_reply", "pns_extract", "voice_call"},
    "pulse": {"enquiry", "buyer_call", "buylead", "wa_msg", "wa_chat"},
    "engagement": {"profile", "bot_call"},
}
SECTION_ORDER = ["header", "guardrails", "threads", "recent", "pulse", "engagement", "opening"]
SECTION_TITLES = {
    "guardrails": "Before you speak",
    "threads": "Open threads",
    "recent": "Last conversations",
    "pulse": "Business pulse (30d | 90d)",
    "engagement": "Engagement history",
    "opening": "Suggested opening (Hinglish)",
}

SUPPORT_HINT = re.compile(
    r"\?|price|rate|charge|kitna|kitne|kab |kaise|plan|payment|paid|refund|problem|issue|help|"
    r"lead|enquir|inquir|call|number|account|login|otp|package|membership|subscription|band|stop|"
    r"chahiye|need|want|not working|nahi aa|"
    r"karna hai|karni hai|karwana|update|catalog|catalogue|listing|photo|add kar|delete|remove|kaise", re.I)
WA_TIME = re.compile(r"((?:aaj|kal|parso|monday|tuesday|wednesday|thursday|friday|saturday|sunday)?\s*(?:subah|dopahar|shaam|"
                     r"sham|raat)?\s*\d{1,2}(?:[:.]\d{2})?\s*(?:baje|bje|am|pm)(?:\s*ke\s*baad)?)", re.I)
CALL_ME = re.compile(r"call (karna|karo|kijiye|kare)|baad mein|busy hoon|abhi busy", re.I)
BUYER_FLOW = re.compile(r"^(Msite_BL|liveCustomer_Buyer|Buy_Product|Enquiry_Media|BUYER_)", re.I)
NEED_PRICE = re.compile(r"need (?:best )?price for (.+)$", re.I)
TIME_PHRASE = re.compile(
    r"((?:after|around|at|by|tomorrow|next|on|in the)\s[^.,;]{2,40}?(?:am|pm|morning|evening|afternoon|week|"
    r"month|monday|tuesday|wednesday|thursday|friday|saturday|sunday|days?|hours?|minutes?|diwali|navratri)\b)",
    re.I)
EXEC_MENTION = re.compile(
    r"already (?:met|spoke|spoken|talked|been (?:in touch|contacted)|in touch|connected|have a meeting|has a meeting)|"
    r"already (?:working|dealing) with|(?:met|spoke|talked) (?:with|to) (?:an? |the )?(?:indiamart )?(?:sales )?executive",
    re.I)
WRONG_NO = re.compile(r"wrong number|not (?:the right person|speaking (?:to|with) )|clarified (?:that )?(?:it|this|he|she) "
                      r"(?:was|is) not|(?:was|is) not [A-Z][\w&.\s]{2,40}(?:Industries|Enterprises?|Traders?|Pvt|Private|"
                      r"Limited|Ltd|Company|Co\b)", re.I)

DISP_SHORT = {"Not Interested": "NI", "General (talked)": "General", "Call Later / Busy": "Call later",
              "Meeting Fixed": "Meeting fixed"}


class Ctx:
    """Everything a builder needs for one GLID at one instant."""

    def __init__(self, glid: int, profile: dict, events: list[dict], now: datetime, cfg: dict,
                 strict_pit: bool = False):
        self.glid, self.p, self.now, self.cfg = glid, profile, now, cfg
        self.strict_pit = strict_pit  # True = ignore profile aggregates (they include later data)
        lb = cfg.get("lookback", {})
        self.detail_days = lb.get("detail_days", 14)
        self.thread_days = lb.get("thread_days", 21)
        self.windows = lb.get("pulse_windows", [30, 90])
        self.max_items = lb.get("max_items_per_section", 4)
        self.by_ch: dict[str, list[dict]] = {}
        for e in events:
            self.by_ch.setdefault(e["channel"], []).append(e)
        self.names = counterpart_names(e["meta"].get("subject") for n in ("enquiry", "enquiry_reply")
                                       for e in self.by_ch.get(n, []))

    def q(self, text, limit: int | None = None) -> str:
        """Clean + strip the other party's personal names before anything is quoted in the file."""
        return clean(scrub_people(clean(text), self.names), limit)

    def ch(self, *names: str, days: int | None = None) -> list[dict]:
        out = [e for n in names for e in self.by_ch.get(n, [])]
        if days is not None:
            cut = self.now - timedelta(days=days)
            out = [e for e in out if e["ts"] >= cut]
        return sorted(out, key=lambda e: e["ts"], reverse=True)

    def flag(self, key: str) -> bool:
        if self.strict_pit:
            return False
        v = self.p.get(key)
        return v is not None and float(v) >= 1


# ------------------------------------------------------------------ header
def build_header(c: Ctx) -> list[str]:
    p = c.p
    if p.get("new_user"):
        return [f"# New contact {c.glid} · first seen on IndiaMART channels recently",
                "**Profile:** not registered yet — everything below comes from their own messages"]
    name = clean(p.get("company_name")) or f"Seller {c.glid}"
    loc_parts: list[str] = []
    for x in (clean(p.get("seller_locality")), clean(p.get("seller_city")), clean(p.get("seller_state"))):
        if x and x.lower() not in {y.lower() for y in loc_parts}:
            loc_parts.append(x.title() if x.isupper() else x)
    loc = ", ".join(loc_parts)
    cats = [clean(p.get(f"top_category_{i}")) for i in (1, 2, 3)]
    cats = [x for x in cats if x]
    bits = [clean(p.get("nature_of_business")), clean(p.get("business_type"))]
    if p.get("annual_turnover"):
        bits.append("₹" + clean(p["annual_turnover"]).replace(" ", ""))
    if p.get("gst_registration_year"):
        bits.append(f"GST since {int(float(p['gst_registration_year']))}")
    snap = " · ".join(b for b in bits if b)
    ncat = p.get("num_categories")
    deals = ", ".join(cats) + (f" (+{int(ncat) - len(cats)} more)" if ncat and int(ncat) > len(cats) else "")
    kyc = {"GST": "gst_verified_flag", "PAN": "is_pan_number_available", "mobile": "mobile_verified_flag",
           "email": "email_verified_flag"}
    kyc_s = " ".join(f"{k}{'✓' if str(p.get(v, 0)) in {'1', '1.0'} else '✗'}" for k, v in kyc.items())
    acct = clean(p.get("customer_type"))
    listing = {"LST": "listed", "TFL": "free-listed", "DNF": "do-not-follow", "NFL": "not listed"}.get(
        str(p.get("listing_status")), clean(p.get("listing_status")))
    cqs = p.get("eng_cqs")
    lines = [f"# {name} · seller · {loc}" if loc else f"# {name} · seller"]
    if snap:
        lines.append(f"**Business:** {snap}")
    if deals:
        lines.append(f"**Deals in:** {deals}")
    acct_line = "**Account:** " + " · ".join(b for b in (acct, listing, f"KYC {kyc_s}") if b and b.strip("-– "))
    if cqs is not None:
        acct_line += f" · catalog score {int(float(cqs))}"
    lines.append(acct_line)
    return lines


# -------------------------------------------------------------- guardrails
def _best_time(c: Ctx) -> str | None:
    hours = [e["ts"].hour for e in c.ch("bot_call")]
    hours += [e["ts"].hour for e in c.ch("exec_call") if e["kind"] == "Answered"]
    hours += [e["ts"].hour for e in c.ch("buyer_call") if e["kind"] == "Connected"]
    if len(hours) < 3:
        return None
    bands = Counter(hour_band(h) for h in hours)
    band, n = bands.most_common(1)[0]
    return f"Best time to reach: {band} (picked up {n} of {len(hours)} answered calls in this slot)"


def build_guardrails(c: Ctx) -> list[str]:
    out: list[str] = []
    if c.flag("do_not_call_requested"):
        out.append("⛔ Asked not to be called earlier → do not pitch; confirm opt-out politely and end.")
    ex = [e for e in c.ch("exec_call", days=c.detail_days) if e["kind"] == "Answered"
          and float(e["meta"].get("call_duration", 0) or 0) >= 45]
    mentioned_exec = [e for e in c.ch("bot_call", days=60) if EXEC_MENTION.search(e.get("text") or "")]
    if ex:
        e = ex[0]
        mins = max(1, round(float(e["meta"].get("call_duration", 0)) / 60))
        out.append(f"Spoke with an IndiaMART executive {rel(e['ts'])} ({e['meta'].get('module', 'call')}, "
                   f"{mins} min) → don't offer a fresh meeting; ask how it went.")
    elif c.flag("already_in_touch_with_executive") or mentioned_exec:
        when = f" (said so {rel(mentioned_exec[0]['ts'])})" if mentioned_exec else ""
        out.append(f"Already in touch with an IndiaMART executive{when} → reference it, don't re-pitch a meeting.")
    wrong = [e for e in c.ch("bot_call", days=60) if WRONG_NO.search(e.get("text") or "")]
    if wrong:
        out.append(f"⚠ Call {rel(wrong[0]['ts'])} reached someone who said this isn't "
                   f"{clean(c.p.get('company_name')) or 'the business'} → confirm identity before pitching.")
    week = c.ch("bot_call", days=7)
    if len(week) >= 2:
        out.append(f"Already reached by VANI {len(week)}× this week → acknowledge it, keep it under a minute.")
    if c.flag("showed_frustration"):
        out.append("Showed frustration on a past call → be brief, offer callback early.")
    if c.flag("asked_if_talking_to_bot"):
        out.append("Has asked if this is a bot → answer honestly if asked again.")
    bt = _best_time(c)
    if bt:
        out.append(bt)
    langs = Counter()
    for e in c.ch("pns_extract"):
        for l in re.findall(r"[A-Za-z]+", str(e["meta"].get("languages", ""))):
            langs[l] += 1
    if langs:
        out.append("Speaks on calls: " + ", ".join(l for l, _ in langs.most_common(2)))
    return out


# ----------------------------------------------------------------- threads
def _later_answered_call(c: Ctx, ev: dict) -> bool:
    calls = c.ch("bot_call", "exec_call", "voice_call")
    key = (ev["ts"], ev.get("id", 0))
    return any((e["ts"], e.get("id", 0)) > key and (e["channel"] != "exec_call" or e["kind"] == "Answered")
               for e in calls)


def open_threads(c: Ctx) -> list[dict]:
    """Structured open threads (also used for the opening line)."""
    th: list[dict] = []
    for e in c.ch(*CHAT_CHANNELS, days=c.thread_days):
        txt = c.q(e.get("text"), 110)
        lab = CHAT_LABEL.get(e["channel"], "WhatsApp")
        intent = str(e["meta"].get("intent", ""))
        if e["kind"] != "typed" or not txt or BUYER_FLOW.match(intent) or not SUPPORT_HINT.search(txt):
            continue
        if _later_answered_call(c, e):
            continue
        tm = WA_TIME.search(txt)
        if CALL_ME.search(txt) and tm:  # "kal shaam 5 baje ke baad call karna" → a callback time, not a question
            th.append({"type": "wa_time", "ts": e["ts"], "text": txt, "when": tm.group(1).strip(), "channel": e["channel"],
                       "line": f"{lab} {rel(e['ts'])}: asked to be called “{tm.group(1).strip()}” — honour this time"})
            break
        th.append({"type": "wa_question", "ts": e["ts"], "text": txt, "channel": e["channel"],
                   "line": f"{lab} {rel(e['ts'])}: “{txt}” — not yet answered on a call"})
        break  # latest one is enough
    for e in c.ch("wa_chat", days=c.thread_days):
        if "Callback" in str(e["meta"].get("intent", "")) and not _later_answered_call(c, e):
            th.append({"type": "wa_callback", "ts": e["ts"],
                       "line": f"Requested a callback on WhatsApp {rel(e['ts'])}"})
            break
    calls = c.ch("bot_call", "voice_call", days=c.thread_days)
    if calls:
        last = calls[0]
        if last["kind"] == "Call Later / Busy":
            m = TIME_PHRASE.search(last.get("text") or "")
            when = f" — asked: “{m.group(1)}”" if m else ""
            th.append({"type": "callback", "ts": last["ts"], "when": m.group(1) if m else None,
                       "line": f"Last VANI call {rel(last['ts'])} ended with ‘call later’{when}"})
        if last["kind"] == "Meeting Fixed":
            th.append({"type": "meeting", "ts": last["ts"],
                       "line": f"Meeting fixed on a {'VANI' if last['channel'] == 'bot_call' else 'voice'} call "
                               f"{rel(last['ts'])} → confirm it happened before any pitch"})
    unread = [e for e in c.ch("enquiry", days=7) if not e["meta"].get("first_read_date")]
    if unread:
        u = unread[0]
        prod = clean(u["meta"].get("product_name"), 40)
        city = clean(u["meta"].get("buyer_city"))
        th.append({"type": "unread", "ts": u["ts"], "n": len(unread), "product": prod,
                   "line": f"{len(unread)} new enquir{'y' if len(unread) == 1 else 'ies'} unread "
                           f"(latest: {prod}{', ' + city if city else ''}, {rel(u['ts'])})"})
    # buyer replied last, seller silent
    threads: dict = {}
    for e in sorted(c.ch("enquiry_reply", days=7), key=lambda e: e["ts"]):
        threads[e["meta"].get("query_id")] = e
    waiting = [e for e in threads.values() if e["kind"] == "buyer"]
    if waiting:
        w = max(waiting, key=lambda e: e["ts"])
        th.append({"type": "buyer_waiting", "ts": w["ts"],
                   "line": f"{len(waiting)} buyer repl{'y' if len(waiting) == 1 else 'ies'} awaiting seller response "
                           f"(latest {rel(w['ts'])}: “{c.q(w.get('text'), 60)}”)"})
    return th[: c.max_items]


def build_threads(c: Ctx) -> list[str]:
    return [t["line"] for t in open_threads(c)]


# ------------------------------------------------------------------ recent
def _summ(text: str | None, limit: int = 120) -> str:
    """Strip boilerplate from bot-call summaries and keep the seller's response."""
    s = clean(text)
    if not s:
        return ""
    sents = re.split(r"(?<=[.!?])\s+", s)
    keep = [x for x in sents if not re.match(r"^(The )?(agent|executive|bot)\b.*\b(called|from IndiaMART)", x, re.I)]
    s = " ".join(keep or sents[1:] or sents)
    s = re.sub(r"\bthe lead\b", "seller", s, flags=re.I)
    s = re.sub(r"\bThe agent\b", "Bot", s)
    s = re.sub(r"\bthe agent\b", "bot", s)
    return clean(s, limit)


def build_recent(c: Ctx) -> list[str]:
    items: list[tuple[datetime, str]] = []
    for e in c.ch("bot_call", "voice_call", days=c.detail_days)[:3]:
        dur = e["meta"].get("lead_call_duration") or e["meta"].get("duration")
        d = f" ({int(float(dur))}s)" if dur else ""
        label = "VANI call" if e["channel"] == "bot_call" else f"Voice call ({e['meta'].get('agent', 'VANI')})"
        items.append((e["ts"], f"{fmt_date(e['ts'])} · {label} · {DISP_SHORT.get(e['kind'], e['kind'])}{d}: "
                               f"{_summ(c.q(e.get('text')))}"))
    for e in c.ch("exec_call", days=c.detail_days)[:2]:
        dur = float(e["meta"].get("call_duration", 0) or 0)
        st = f"answered, {max(1, round(dur / 60))} min" if e["kind"] == "Answered" else "not answered"
        items.append((e["ts"], f"{fmt_date(e['ts'])} · Executive call ({e['meta'].get('module', '')}) · {st}"))
    wa = [e for e in c.ch(*CHAT_CHANNELS, days=c.detail_days) if e["kind"] in {"typed", "image/jpeg", "DOCUMENT", "document"}]
    open_q = {t.get("text") for t in open_threads(c) if t["type"] == "wa_question"}
    if wa and clean(wa[0].get("text"), 110) in open_q:  # already shown under Open threads
        wa = wa[1:]
    if wa:
        e = wa[0]
        txt = c.q(e.get("text"), 70) or ("shared an image" if "image" in e["kind"] else "shared a document")
        m = NEED_PRICE.search(txt)
        if m:
            txt = f"was sourcing ‘{clean(m.group(1), 50)}’ as a buyer"
        chans = {x["channel"] for x in wa}
        count = f"{len(wa)} msgs in {c.detail_days}d" if chans == {e["channel"]} else             f"{len(wa)} chat msgs in {c.detail_days}d across " + " + ".join(CHAT_LABEL[ch] for ch in CHAT_CHANNELS if ch in chans)
        items.append((e["ts"], f"{fmt_date(e['ts'])} · {CHAT_LABEL.get(e['channel'], 'WhatsApp')} ({count}): {txt}"))
    rep = [e for e in c.ch("enquiry_reply", days=c.detail_days) if e["kind"] == "seller"]
    if rep:
        quote = c.q(rep[0].get("text"), 60)
        items.append((rep[0]["ts"], f"{fmt_date(rep[0]['ts'])} · Replied to {len(rep)} buyer enquir"
                                    f"{'y' if len(rep) == 1 else 'ies'}" + (f": “{quote}”" if quote else "")))
    px = [e for e in c.ch("pns_extract", days=c.detail_days)]
    if px:
        e = px[0]
        role = "as buyer" if e["kind"] == "BUYER" else "as seller"
        items.append((e["ts"], f"{fmt_date(e['ts'])} · Phone call {role} about {clean(e.get('text'), 50)}"))
    items.sort(key=lambda x: x[0], reverse=True)
    if not items:  # fall back to the last touch outside the detail window
        last = c.ch("bot_call", "exec_call")
        if last:
            e = last[0]
            items.append((e["ts"], f"{fmt_date(e['ts'])} · last contact: {e['channel'].replace('_', ' ')} "
                                   f"({e['kind']}), {rel(e['ts'])}"))
    return [x[1] for x in items[: c.max_items]]


# ------------------------------------------------------------------- pulse
def _top(counts: Counter, n: int) -> list[str]:
    """Most common values, merging case variants ("maid service" / "Maid Service")."""
    merged: Counter = Counter()
    label: dict[str, str] = {}
    for v, k in counts.most_common():
        key = v.lower().strip()
        merged[key] += k
        label.setdefault(key, v)
    return [label[k] for k, _ in merged.most_common(n)]


def build_pulse(c: Ctx) -> list[str]:
    w1, w2 = c.windows[0], c.windows[-1]
    out: list[str] = []
    enq1, enq2 = c.ch("enquiry", days=w1), c.ch("enquiry", days=w2)
    if enq2:
        read = sum(1 for e in enq2 if e["meta"].get("first_read_date"))
        prods = Counter(clean(e["meta"].get("product_name"), 35) for e in enq2 if e["meta"].get("product_name"))
        cities = Counter(clean(e["meta"].get("buyer_city")) for e in enq2 if e["meta"].get("buyer_city"))
        top = ", ".join(_top(prods, 2))
        cty = ", ".join(_top(cities, 2))
        out.append(f"Enquiries: {len(enq1)} | {len(enq2)} · opened {pct(read, len(enq2))}"
                   + (f" · top: {top}" if top else "") + (f" · buyers from {cty}" if cty else ""))
    bc1, bc2 = c.ch("buyer_call", days=w1), c.ch("buyer_call", days=w2)
    if bc2:
        con = sum(1 for e in bc2 if e["kind"] == "Connected")
        out.append(f"Buyer calls: {len(bc1)} | {len(bc2)} · answered {pct(con, len(bc2))}")
    bl1, bl2 = c.ch("buylead", days=w1), c.ch("buylead", days=w2)
    if bl2:
        cred = sum(float(e["meta"].get("credits_used", 0) or 0) for e in bl2)
        kws = Counter(clean(e.get("text"), 30) for e in bl2 if e.get("text"))
        kw = ", ".join(_top(kws, 2))
        out.append(f"Buy-leads bought: {len(bl1)} | {len(bl2)} ({cred:,.0f} credits)" + (f" · {kw}" if kw else ""))
    wa = c.ch("wa_msg", days=w1)
    if wa:
        sent = [e for e in wa if e["kind"] == "API"]
        read = sum(1 for e in sent if str(e["meta"].get("message_status", "")).lower() == "read")
        user = sum(1 for e in wa if e["kind"] == "USER")
        out.append(f"WhatsApp ({w1}d): {len(sent)} from IndiaMART, {pct(read, len(sent))} read · "
                   f"{user} messages from seller")
    buying = []
    for e in c.ch("wa_chat", days=w2):
        m = NEED_PRICE.search(str(e.get("text") or ""))
        if m:
            buying.append(clean(m.group(1).split(",")[0], 40))
    if buying:
        out.append("Also sourcing as a buyer: " + ", ".join(_top(Counter(buying), 2)))
    return out


# -------------------------------------------------------------- engagement
def build_engagement(c: Ctx) -> list[str]:
    out: list[str] = []
    calls = c.ch("bot_call")
    if calls:
        disp = Counter(DISP_SHORT.get(e["kind"], e["kind"]) for e in calls)
        durs = [float(e["meta"].get("lead_call_duration", 0) or 0) for e in calls]
        avg = sum(durs) / len(durs) if durs else 0
        out.append(f"VANI calls answered since Apr: {len(calls)} · " +
                   ", ".join(f"{k} {v}" for k, v in disp.most_common()) + f" · avg {avg:.0f}s")
    if not c.strict_pit:
        att, rate = c.p.get("bot_attempts"), c.p.get("bot_answer_rate")
        if att:
            out.append(f"Pickup: {int(att)} dial attempt{'s' if int(att) != 1 else ''}, "
                       f"answer rate {float(rate or 0) * 100:.0f}%")
        for key, label in (("past_objections", "Past objections"), ("past_questions_asked", "Questions they ask")):
            v = clean(c.p.get(key), 120)
            if v:
                out.append(f"{label}: {v}")
    return out


BUILDERS = {
    "header": build_header,
    "guardrails": build_guardrails,
    "threads": build_threads,
    "recent": build_recent,
    "pulse": build_pulse,
    "engagement": build_engagement,
}


# ----------------------------------------------------------- opening line
def opening_line(c: Ctx) -> str:
    """Rule-based personalised opener (LLM can rewrite it when available)."""
    name = clean(c.p.get("company_name"))
    intro = (f"Namaste, kya meri baat {name} se ho rahi hai? Main IndiaMART se Payal bol rahi hoon." if name
             else "Namaste ji, main IndiaMART se Payal bol rahi hoon.")
    if c.flag("do_not_call_requested"):
        return (f"{intro} Aapne pehle call na karne ko kaha tha — bas confirm karna tha, "
                f"kya main aapka number calling list se hata doon?")
    th = {t["type"]: t for t in open_threads(c)}
    if any(WRONG_NO.search(e.get("text") or "") for e in c.ch("bot_call", days=60)[:2]):
        return (f"Namaste ji, main IndiaMART se Payal bol rahi hoon. Kya yeh {name} ka number hai? "
                f"Pichhli baar shayad galat vyakti se baat ho gayi thi, isliye confirm kar rahi hoon.")
    week = len(c.ch("bot_call", days=7))
    sorry = " Is hafte pehle bhi call kiya tha, isliye bas ek minute loongi." if week >= 2 else ""
    if "wa_time" in th:
        t = th["wa_time"]
        return (f"{intro} Aapne {CHAT_LABEL_HI.get(t.get('channel'), 'WhatsApp par')} {t['when'].lower()} call karne ko kaha tha, isliye abhi call kiya hai — "
                f"kya abhi baat karna theek rahega?")
    if "wa_question" in th:
        t = th["wa_question"]
        verb = "poochha" if re.search(r"\?|kya|kitna|kitne|kaise|kab|kaun", t["text"], re.I) else "likha"
        return (f"{intro} Aapne {rel_hi(t['ts'])} {CHAT_LABEL_HI.get(t.get('channel'), 'WhatsApp par')} {verb} tha — “{clean(t['text'], 60)}” — "
                f"usi ke baare mein baat karne ke liye call kiya hai.{sorry or ' Do minute milenge?'}")
    if "callback" in th or "wa_callback" in th:
        return (f"{intro} Pichhli baar aapne baad mein call karne ko kaha tha, isliye abhi call kiya hai — "
                f"kya abhi do minute baat ho sakti hai?")
    if "meeting" in th:
        return (f"{intro} {rel_hi(th['meeting']['ts'], cap=True)} aapki hamare executive ke saath meeting "
                f"fix hui thi — kya woh meeting ho gayi?")
    ex = [e for e in c.ch("exec_call", days=c.detail_days) if e["kind"] == "Answered"]
    if ex:
        return (f"{intro} {rel_hi(ex[0]['ts'], cap=True)} hamare executive ki aapse baat hui thi — "
                f"kya aapka kaam aage badha? Koi madad chahiye toh batayein.")
    if "unread" in th:
        t = th["unread"]
        return (f"{intro} Aapke paas {t['product']} ke liye {t['n']} nayi buyer enquiry aayi hai jo abhi "
                f"dekhi nahi gayi — kya main details bata doon?")
    bl = c.ch("buylead", days=30)
    if bl and bl[0].get("text"):
        return (f"{intro} Aap {clean(bl[0]['text'], 40)} ke buy-leads le rahe hain — "
                f"kaisa response mil raha hai buyers se?")
    cat = clean(c.p.get("top_category_1"))
    city = clean(c.p.get("seller_city"))
    if sorry:
        return f"{intro}{sorry} Aapke {cat or 'business'} ke liye buyers ki enquiries badhane mein madad karni thi."
    if cat:
        return (f"{intro} {city + ' mein ' if city else ''}{cat} ke liye buyers ki enquiries aa rahi hain — "
                f"isi par aapse do minute baat karni thi.")
    return f"{intro} Aapke IndiaMART account ke baare mein do minute baat karni thi."
