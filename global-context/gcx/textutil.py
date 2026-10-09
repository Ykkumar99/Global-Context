"""Small text helpers: token estimates, PII masking, relative dates, cleanup."""
from __future__ import annotations

import re
from datetime import datetime

_PHONE = re.compile(r"(?<!\d)(?:\+?91[\s-]?)?[6-9]\d{2}[\s-]?\d{3}[\s-]?\d{4}(?!\d)")
_LANDLINE = re.compile(r"(?<!\d)0?\d{2,4}[\s-]?\d{6,8}(?!\d)")
_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")
_URL = re.compile(r"https?://\S+")
_WS = re.compile(r"\s+")


def est_tokens(text: str) -> int:
    """Approximate LLM tokens (~4 chars/token for English/Hinglish romanised)."""
    return max(1, round(len(text) / 4))


def mask_pii(text: str) -> str:
    text = _EMAIL.sub("[email]", text)
    text = _PHONE.sub("[phone]", text)
    text = _LANDLINE.sub("[phone]", text)
    return text


def clean(text, limit: int | None = None, strip_urls: bool = True) -> str:
    if text is None:
        return ""
    s = str(text)
    if s.lower() in {"nan", "none", "null", "-", "info_na"}:
        return ""
    if strip_urls:
        s = _URL.sub("", s)
    s = s.replace("*", "").replace("|", "/")
    s = mask_pii(_WS.sub(" ", s)).strip(" ,.-")
    if limit and len(s) > limit:
        cut = s[: limit - 1]
        cut = cut.rsplit(" ", 1)[0] if " " in cut[-20:] else cut
        s = cut + "…"
    return s


def ago(ts: datetime, now: datetime) -> str:
    secs = (now - ts).total_seconds()
    if secs < 90:
        return "just now"
    if secs < 3600:
        return f"{int(secs // 60)}m ago"
    if secs < 86400:
        return f"{int(secs // 3600)}h ago"
    days = int(secs // 86400)
    return "yesterday" if days == 1 else f"{days}d ago"


def fmt_date(ts: datetime) -> str:
    return ts.strftime("%d %b")


def pct(num: float, den: float) -> str:
    return f"{(100 * num / den):.0f}%" if den else "–"


def hour_band(h: int) -> str:
    if h < 11:
        return "9–11 AM"
    if h < 13:
        return "11 AM–1 PM"
    if h < 15:
        return "1–3 PM"
    if h < 17:
        return "3–5 PM"
    if h < 19:
        return "5–7 PM"
    return "7–9 PM"


# ---- time markers: sections store absolute times, rendering resolves them
_MARK = re.compile(r"⟦(hi|en)\|(\d{4}-\d\d-\d\d \d\d:\d\d:\d\d)(\|cap)?⟧")


def rel(ts: datetime) -> str:
    """Placeholder for 'N days ago' resolved at render time (keeps cached sections time-independent)."""
    return f"⟦en|{ts:%Y-%m-%d %H:%M:%S}⟧"


def rel_hi(ts: datetime, cap: bool = False) -> str:
    return f"⟦hi|{ts:%Y-%m-%d %H:%M:%S}{'|cap' if cap else ''}⟧"


def hi_ago(ts: datetime, now: datetime) -> str:
    secs = (now - ts).total_seconds()
    if secs < 3 * 3600:
        return "abhi thodi der pehle"
    d = int(secs // 86400)
    return "aaj" if d == 0 else "kal" if d == 1 else f"{d} din pehle"


def resolve_times(text: str, now: datetime) -> str:
    def sub(m):
        ts = datetime.strptime(m.group(2), "%Y-%m-%d %H:%M:%S")
        out = ago(ts, now) if m.group(1) == "en" else hi_ago(ts, now)
        return out[:1].upper() + out[1:] if m.group(3) else out
    return _MARK.sub(sub, text)


# ---- cross-party privacy: the bot must never reveal one party's personal details to another
_SALUTE = re.compile(r"\b(Hi|Hello|Dear|Hey|Namaste|Respected|Mr\.?|Mrs\.?|Ms\.?|Sir|Madam)\s+([A-Z][A-Za-z.]+(?:\s+[A-Z][a-z]+)?)")
_FROM = re.compile(r"\bfrom\s+(.+?)\s+via IndiaMART", re.I)
_TO = re.compile(r"^\s*([^,]{2,40}),\s+you have received", re.I)
_RE = re.compile(r"\bfrom\s+([A-Z][\w.]+(?:\s+[A-Z][\w.]+)?)\b")


def counterpart_names(subjects) -> set[str]:
    """Personal names of the other party, harvested from enquiry / reply subjects."""
    out: set[str] = set()
    for s in subjects:
        if not s:
            continue
        for pat in (_FROM, _TO):
            m = pat.search(str(s))
            if m:
                for tok in re.findall(r"[A-Za-z]{3,}", m.group(1)):
                    out.add(tok.lower())
    return out - {"indiamart", "via", "the", "and", "enquiry", "buyer", "sir", "madam"}


def scrub_people(text: str, names: set[str] | None = None) -> str:
    """Remove the other party's personal names (salutations + harvested names)."""
    if not text:
        return text
    t = _SALUTE.sub(lambda m: f"{m.group(1)} [buyer]", text)
    if names:
        t = re.sub(r"\b(" + "|".join(re.escape(n) for n in sorted(names, key=len, reverse=True)) + r")\b",
                   "[buyer]", t, flags=re.I)
    return re.sub(r"(\[buyer\]\s*){2,}", "[buyer] ", t)
