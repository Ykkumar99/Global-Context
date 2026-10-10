"""buyer.md builder from IndiaMART's existing ``getContext`` API response.

The API already aggregates buyer activity, KYC, WhatsApp chats, leads and
tickets — but returns 7–33 KB of nested JSON per user. This module distils it
into a ~300-token, voice-ready brief.
"""
from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from datetime import datetime
from urllib.parse import unquote_plus

from .textutil import clean, fmt_date, rel

ACT_LABEL1 = {"ENQ": "enquiry", "C2C": "call to a seller", "BL": "requirement posted", "Browse": "view",
              "Search": "search"}
ACT_LABEL = {"ENQ": "enquiries", "C2C": "calls to sellers", "BL": "requirements posted",
             "Browse": "views", "Search": "searches"}


def _dt(s: str | None) -> datetime | None:
    if not s:
        return None
    s = str(s)
    for fmt, n in (("%Y%m%d%H%M%S", 14), ("%Y-%m-%d %H:%M:%S", 19), ("%Y-%m-%dT%H:%M:%S", 19)):
        try:
            return datetime.strptime(s[:n], fmt)
        except ValueError:
            continue
    return None


def snapshot_time(data: dict) -> datetime:
    t = (data.get("activitydetails") or {}).get("upload_metadata", {}).get("upload_time")
    return _dt(t) or datetime.now()


def _wa_content(chat: dict) -> dict:
    raw = chat.get("CHAT_CONTENT") or ""
    try:
        mc = json.loads(raw).get("message_content") or {}
    except (ValueError, AttributeError):
        mc = {"text": raw}
    return mc if isinstance(mc, dict) else {"text": str(mc)}


def _wa_raw(chat: dict) -> str:
    mc = _wa_content(chat)
    return str(mc.get("text") or mc.get("caption")
               or ((mc.get("interactive") or {}).get("body") or {}).get("text") or "")


def _wa_text(chat: dict) -> str:
    """Extract human text from a LAST_WA*_CHAT entry (nested, escaped JSON)."""
    return clean(_wa_raw(chat).replace("\\n", " "), 110)


SPOKE = re.compile(r"You just spoke with \*([^*]+)\*", re.I)
TRIED = re.compile(r"\*([^*]+)\* tried to reach you", re.I)
RESPONDED = re.compile(r"\n\n(.+?) \((?:[^)]*)\)(?: \(also deals in [^)]*\))? responded to your (.+?) enquiry", re.S)


def wa_events(data: dict) -> list[dict]:
    """Classify the buyer's recent WhatsApp messages into conversation facts."""
    act = data.get("activitydetails") or {}
    chats = (act.get("LAST_WA9696_CHAT") or []) + (act.get("LAST_WA8181_CHAT") or [])
    out = []
    for ch in chats:
        ts = _dt(ch.get("ENTRY_DATE"))
        raw = _wa_raw(ch)
        if not ts or not raw.strip():
            continue
        if ch.get("MESSAGE_SENDER") == "USER":
            txt = clean(re.sub(r"https?://\S+", "", raw), 110)
            m = re.search(r"need (?:best )?price for (.+)", txt, re.I)
            if m:
                out.append({"ts": ts, "type": "price_ask", "item": clean(m.group(1), 50)})
            elif len(txt) > 3 and txt.lower() not in {"hi", "hello", "yes", "no", "ok", "stop"}:
                out.append({"ts": ts, "type": "said", "text": txt})
            continue
        for pat, typ in ((SPOKE, "spoke"), (TRIED, "missed")):
            m = pat.search(raw)
            if m:
                out.append({"ts": ts, "type": typ, "seller": clean(m.group(1), 40)})
                break
        else:
            m = RESPONDED.search(raw)
            if m:
                out.append({"ts": ts, "type": "responded", "seller": clean(m.group(1), 40), "item": clean(m.group(2), 40)})
    return sorted(out, key=lambda x: x["ts"], reverse=True)


def _short(name: str, n: int = 45) -> str:
    return clean(re.split(r"\s[\(\[]|,", name or "")[0], n)


def _activities(data: dict) -> list[dict]:
    acts = (data.get("activitydetails") or {}).get("BUYER_ACTIVITY") or []
    out = []
    for a in acts:
        ts = _dt(a.get("ACTIVITY_TIME"))
        if not ts:
            continue
        # search keywords arrive URL-encoded ("sticky%20mats") — decode so they merge with the category
        cat = clean(unquote_plus(str(a.get("CATEGORY_NAME") or "")))
        kw = clean(unquote_plus(str(a.get("KEYWORD") or "")))
        out.append({"ts": ts, "type": a.get("ACTIVITY_TYPE"), "cat": cat, "kw": kw,
                    "seller": a.get("SELLER_GLUSR_ID") if a.get("SELLER_GLUSR_ID") not in (None, "0") else None})
    return sorted(out, key=lambda x: x["ts"], reverse=True)


def interests(data: dict, top: int = 3) -> list[dict]:
    """Rank categories the buyer is actively pursuing (enquiry/call > search > view)."""
    weight = {"ENQ": 5, "C2C": 6, "BL": 6, "Search": 2, "Browse": 1, "Others": 0}
    score: dict[str, float] = defaultdict(float)
    counts: dict[str, Counter] = defaultdict(Counter)
    kws: dict[str, Counter] = defaultdict(Counter)
    sellers: dict[str, set] = defaultdict(set)
    last: dict[str, datetime] = {}
    for a in _activities(data):
        name = a["cat"] if a["cat"] and a["cat"] != "-" else a["kw"]
        if not name:
            continue
        key = name.title()
        score[key] += weight.get(a["type"], 0)
        counts[key][a["type"]] += 1
        if a["kw"]:
            kws[key][a["kw"]] += 1
        if a["seller"]:
            sellers[key].add(a["seller"])
        last[key] = max(last.get(key, a["ts"]), a["ts"])
    ranked = sorted(score, key=lambda k: (score[k], last[k]), reverse=True)
    return [{"name": k, "score": score[k], "counts": counts[k], "sellers": len(sellers[k]), "last": last[k],
             "kw": kws[k].most_common(1)[0][0] if kws[k] else None} for k in ranked[:top] if score[k] > 0]


def build_buyer_md_parts(glid: int, data: dict) -> tuple[dict[str, list[str]], str, dict]:
    now = snapshot_time(data)
    kyc = data.get("kycdetails") or {}
    act = data.get("activitydetails") or {}
    tick = data.get("ticketsdetails") or {}
    bl = data.get("BLdetails") or {}
    name = clean(kyc.get("customer_name")) or clean(kyc.get("first_name")) or f"Buyer {glid}"
    company = clean(kyc.get("company_name"))
    city = clean(kyc.get("city"))
    sec: dict[str, list[str]] = {}

    head = [f"# {name}" + (f" · {company}" if company else "") + " · buyer" + (f" · {city}" if city else "")]
    ctype = clean(kyc.get("customer_type"))
    acct = [ctype] if ctype.strip("-– ") else []
    vint = clean(kyc.get("registered_since_with_indiamart"))
    if vint:
        acct.append(f"on IndiaMART {vint.replace(' 0 M', '').replace(' Y', 'y').replace(' M', 'm')}")
    if kyc.get("avg_rating_count"):
        acct.append(f"rated {kyc['avg_rating_count']}★ ({kyc.get('rating_count', 0)})")
    if acct:
        head.append("**Account:** " + " · ".join(acct))
    ok = lambda v: "✓" if str(v).lower() in {"verified", "true", "yes", "1"} else "✗"  # noqa: E731
    head.append(f"**KYC:** mobile{ok(kyc.get('input_mobile_verification_status'))} "
                f"email{ok(kyc.get('input_email_verification_status'))} GST{ok(kyc.get('gst_status'))} "
                f"address{ok(kyc.get('address_verification_status'))}"
                + (" · account under review" if kyc.get("glusr_usr_approv") not in (None, "", "A") else ""))
    sec["header"] = head

    # ---- guardrails
    g: list[str] = []
    l7 = tick.get("last_7_days") or {}
    l90 = tick.get("last_8_to_90_days") or {}
    neg = sum(int(l7.get(k, 0) or 0) for k in ("irate_complaint_count", "negative_feedback_count",
                                                 "whatsapp_negative_feedback_count"))
    if neg:
        g.append(f"⚠ {neg} complaint/negative feedback in the last 7 days → acknowledge before anything else.")
    tot90 = int(l90.get("total_ticket_count", 0) or 0)
    if tot90:
        g.append(f"{tot90} support ticket(s) in the last 90 days.")
    if str(kyc.get("high_risk_suspected", "")).lower() == "yes":
        g.append("⚠ Flagged high-risk → do not share seller contacts without verification.")
    am = (kyc.get("account_manager_bd") or {}).get("name")
    if am:
        g.append("Has a dedicated IndiaMART account manager → offer to loop them in (never share their contact).")
    sec["guardrails"] = g

    # ---- what they want (+ enquiry status)
    w: list[str] = []
    wev = wa_events(data)
    acts = _activities(data)
    enq = [a for a in acts if a["type"] in ("ENQ", "C2C", "BL")]
    contacted = {a["seller"] for a in enq if a["seller"]}
    responded = {e["seller"] for e in wev if e["type"] == "responded"}
    spoke_set = {e["seller"] for e in wev if e["type"] == "spoke"}
    missed_set = {e["seller"] for e in wev if e["type"] == "missed"}
    if enq or responded or spoke_set:
        parts = [f"{sum(1 for a in enq if a['type'] == 'ENQ')} enquiries · {sum(1 for a in enq if a['type'] == 'C2C')} "
                 f"calls to sellers · sellers contacted: {len(contacted)}"]
        if responded or spoke_set or missed_set:
            parts.append(f"{len(responded)} responded, spoke with {len(spoke_set)}, {len(missed_set)} missed calls")
        w.append("Enquiry status: " + " · ".join(parts))
    ints = interests(data)
    for it in ints:
        cnt = ", ".join(f"{n} {ACT_LABEL[t] if n != 1 else ACT_LABEL1[t]}" for t, n in it["counts"].most_common(3)
                        if t in ACT_LABEL)
        extra = f" · contacted {it['sellers']} seller{'s' if it['sellers'] != 1 else ''}" if it["sellers"] else ""
        kw = f" (e.g. “{_short(it['kw'])}”)" if it["kw"] and _short(it["kw"]).lower() != _short(it["name"]).lower() else ""
        w.append(f"{_short(it['name'], 50)}{kw}: {cnt}{extra} · last {rel(it['last'])}")
    le = act.get("LAST_ENQUIRY") or {}
    le_title = clean(unquote_plus(str(le.get("TITLE") or "")), 60)
    if le_title.strip("“”\"' "):
        w.append(f"Last enquiry: “{le_title}”")
    ll = dict(act.get("LAST_LEAD") or {})
    if ll.get("TITLE"):  # requirement titles can also arrive URL-encoded
        ll["TITLE"] = unquote_plus(str(ll["TITLE"]))
    if ll.get("TITLE") and "create bl title" not in ll["TITLE"].lower():
        d = _dt(ll.get("DATE_R"))
        w.append(f"Latest requirement posted: “{clean(ll['TITLE'], 60)}”" + (f" ({fmt_date(d)})" if d else ""))
    active = bl.get("active_bl_details") or []
    if active:
        w.append(f"{len(active)} live requirement(s): " + ", ".join(clean(a.get("ETO_OFR_TITILE"), 40) for a in active[:2]))
    sec["wants"] = w

    # ---- last conversations (WhatsApp + calls)
    r: list[str] = []
    spoke = [e for e in wev if e["type"] == "spoke"]
    if spoke:
        names = list(dict.fromkeys(e["seller"] for e in spoke))
        r.append(f"{fmt_date(spoke[0]['ts'])} · Spoke on phone with {', '.join(names[:3])}"
                 + (f" +{len(names) - 3} more" if len(names) > 3 else "") + " (via IndiaMART)")
    missed = [e for e in wev if e["type"] == "missed"]
    if missed:
        r.append(f"{fmt_date(missed[0]['ts'])} · Missed calls from {', '.join(dict.fromkeys(e['seller'] for e in missed[:3]))}")
    resp = [e for e in wev if e["type"] == "responded"]
    if resp:
        r.append(f"{fmt_date(resp[0]['ts'])} · {resp[0]['seller']} responded to their {resp[0]['item']} enquiry")
    for e in [e for e in wev if e["type"] in ("said", "price_ask")][:2]:
        txt = e.get("text") or f"asked best price for {e['item']}"
        r.append(f"{fmt_date(e['ts'])} · WhatsApp (buyer): “{txt}”")
    conn = data.get("connectdetails") or {}
    if clean(conn.get("last_call_summary")):
        r.append("Last call: " + clean(conn["last_call_summary"], 120))
    sec["recent"] = r

    # ---- signals
    s: list[str] = []
    a30, a90 = act.get("enq_last_30_days", 0), act.get("enq_last_90_days", 0)
    acts = _activities(data)
    by_type = Counter(a["type"] for a in acts)
    # last active = newest touch anywhere (activity log, posted requirement, WhatsApp), not just the activity log
    lead_d = _dt(ll.get("DATE_R")) if ll.get("TITLE") else None
    touches = [t for t in [acts[0]["ts"] if acts else None, lead_d, wev[0]["ts"] if wev else None] if t]
    if acts:
        span = (acts[0]["ts"] - acts[-1]["ts"]).days + 1
        parts = [f"{n} {ACT_LABEL[t] if n != 1 else ACT_LABEL1[t]}" for t, n in by_type.most_common() if t in ACT_LABEL]
        if parts:
            s.append("Recent activity: " + ", ".join(parts[:4]) + f" over {span}d · last active {rel(max(touches))}")
    elif touches:
        s.append(f"Last active {rel(max(touches))}")
    if a30 or a90:
        s.append(f"As a seller: enquiries received 30d | 90d: {a30} | {a90}")
    sec["signals"] = s

    # ---- opening line
    first = (clean(kyc.get("first_name")) or name.split(" ")[0]).title()
    intro = f"Namaste {first} ji, main IndiaMART se Ananya bol rahi hoon."
    lead_title = clean(ll.get("TITLE"), 50) if ll.get("TITLE") and "create bl title" not in ll["TITLE"].lower() else ""
    lead_dt = _dt(ll.get("DATE_R"))
    said = [e for e in wev if e["type"] == "said"
            and ("?" in e["text"] or re.search(r"rate|price|kitna|kab|chahiye", e["text"], re.I))]
    days = lambda ts: (now - ts).days  # noqa: E731
    if neg:
        opening = f"{intro} Aapki haal hi ki shikayat humein mili hai — pehle main usi mein aapki madad karna chahti hoon."
    elif said and days(said[0]["ts"]) <= 7:
        opening = (f"{intro} Aapne WhatsApp par poochha tha — “{clean(said[0]['text'], 60)}” — "
                   f"usi ke liye sahi suppliers ke saath help karne ke liye call kiya hai.")
    elif spoke and days(spoke[0]["ts"]) <= 3:
        names = list(dict.fromkeys(e["seller"] for e in spoke))[:2]
        what = f"{lead_title} ke liye " if lead_title else ""
        opening = (f"{intro} Aapne {what}{' aur '.join(names)} se baat ki thi — kya baat aage badhi, "
                   f"ya main aapko kuch aur verified suppliers se connect karoon?")
    elif lead_title and lead_dt and days(lead_dt) <= 7:
        opening = (f"{intro} Aapne {lead_title} ki requirement daali thi — kya aapko sahi supplier mil gaya, "
                   f"ya main kuch aur options bhejoon?")
    elif ints:
        it = ints[0]
        prod = _short(it["kw"] or it["name"])
        if it["counts"].get("ENQ") or it["counts"].get("C2C"):
            opening = (f"{intro} Aapne {prod} ke liye sellers se baat ki thi — kya aapko sahi rate aur supplier mil gaya, "
                       f"ya main aur verified sellers connect karoon?")
        else:
            opening = f"{intro} Aap {prod} dekh rahe the — kya main aapko kuch verified suppliers connect kar doon?"
    elif lead_title:
        opening = f"{intro} Aapki {lead_title} ki requirement ke baare mein call kiya hai."
    else:
        opening = f"{intro} Aapko kis product ki zaroorat hai, main sahi suppliers dhoondhne mein madad kar sakti hoon."
    meta = {"as_of": now, "name": name, "interests": [i["name"] for i in ints]}
    return sec, opening, meta


BUYER_TITLES = {
    "guardrails": "Before you speak",
    "wants": "What they are looking for",
    "recent": "Last conversations",
    "signals": "Engagement signals",
    "opening": "Suggested opening (Hinglish)",
}
BUYER_ORDER = ["header", "guardrails", "wants", "recent", "signals", "opening"]


def strip_pii(data: dict) -> dict:
    """Remove emails/phones/employee emails before storing demo snapshots."""
    drop = {"email1", "email", "did", "phone_number", "number", "address"}
    email = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")
    phone = re.compile(r"(?<!\d)(?:91)?[6-9]\d{9}(?!\d)")

    def walk(x):
        if isinstance(x, dict):
            return {k: ("" if k in drop and isinstance(v, (str, int)) else walk(v)) for k, v in x.items()}
        if isinstance(x, list):
            return [walk(v) for v in x]
        if isinstance(x, str):
            return phone.sub("", email.sub("", x))
        return x

    return walk(data)
