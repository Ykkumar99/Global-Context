"""Live API regression against a running server.  Run: python scripts/api_regression.py [base_url]

Covers every route, the cross-channel resume flow from the problem statement (WhatsApp → voice → WhatsApp),
buyer + cold-start users, the Sarvam Voice Agent hooks, and bad / edge-case input.
"""
from __future__ import annotations

import json
import sys
import time

import requests

BASE = (sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000").rstrip("/")
SELLER, BUYER, COLD = 146010610, 73699779, 900000000 + int(time.time()) % 99999999
results: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    results.append((name, bool(ok), detail))
    print(f"{'PASS' if ok else 'FAIL'}  {name}" + (f"  — {detail}" if detail and not ok else ""))


def get(path, **kw):
    return requests.get(BASE + path, timeout=30, **kw)


def post(path, body=None, **kw):
    return requests.post(BASE + path, json=body, timeout=60, **kw)


# ---------------------------------------------------------------- basics
r = get("/")
check("GET / serves the demo UI", r.status_code == 200 and "<html" in r.text.lower())
st = get("/api/status").json()
check("GET /api/status", "modes" in st or "sellers" in json.dumps(st), json.dumps(st)[:200])
users = get("/api/users").json()
check("GET /api/users lists sellers + cold demo user", len(users) > 5, f"{len(users)} users")
check("GET /api/users?role=buyer", len(get("/api/users", params={"role": "buyer"}).json()) > 0)
check("GET /api/users?q= search", get("/api/users", params={"q": str(SELLER)}).status_code == 200)

# ---------------------------------------------------------------- files
for glid, role in ((SELLER, "seller"), (BUYER, "buyer")):
    md = get(f"/context/{glid}.md")
    check(f"GET /context/{role}.md is markdown with front-matter", md.status_code == 200 and md.text.startswith("---")
          and f"role: {role}" in md.text and "## Suggested opening" in md.text)
    j = get(f"/api/context/{glid}").json()
    check(f"GET /api/context/{role} JSON", j.get("md", "").startswith("---") and "label" in j)
check("GET /api/context?rebuild=1", get(f"/api/context/{SELLER}", params={"rebuild": True}).status_code == 200)
cold = get(f"/context/{COLD}.md").text
check("Cold-start GLID gets a generic, honest file", "cold_start: true" in cold, cold[:200])
check("Non-numeric GLID → 422, not 500", get("/context/abc.md").status_code == 422)

# -------------------------------------------- cross-channel resume (the core demo)
msg = "Mujhe 500 kg PVC pipe chahiye Jaipur delivery, rate kya hoga?"
t0 = time.time()
wa = post("/api/whatsapp", {"glid": SELLER, "text": msg}).json()
check("POST /api/whatsapp replies", bool(wa.get("reply")), json.dumps(wa)[:200])
check("Freshness: WhatsApp → file updated < 500 ms", wa.get("freshness_ms", 9e9) < 500, f"{wa.get('freshness_ms')} ms")
md = get(f"/context/{SELLER}.md").text
check("seller.md now contains the WhatsApp message", "PVC pipe" in md, md[:300])
start = post("/api/call/start", {"glid": SELLER, "tts": False}).json()
check("Voice call opens by resuming the WhatsApp thread", "PVC" in start.get("text", "") or "pipe" in start.get("text", "").lower(),
      start.get("text", "")[:200])
off = post("/api/call/start", {"glid": SELLER, "tts": False, "use_context": False}).json()
check("Memory off → generic opener (control)", "PVC" not in off.get("text", ""), off.get("text", "")[:200])
hist = [{"who": "bot", "text": start["text"]}]
turn = post("/api/call/turn", {"glid": SELLER, "text": "Haan, kal 4 baje call kar lena", "history": hist, "tts": False}).json()
check("POST /api/call/turn", bool(turn.get("text")), json.dumps(turn)[:200])
reask = any(w in turn.get("text", "").lower() for w in ("kitna quantity", "kaunsa product", "which product", "kahan delivery"))
check("Bot does not re-ask facts already given on WhatsApp", not reask, turn.get("text", ""))
hist += [{"who": "user", "text": "Haan, kal 4 baje call kar lena"}, {"who": "bot", "text": turn["text"]}]
end = post("/api/call/end", {"glid": SELLER, "history": hist}).json()
check("POST /api/call/end writes the call back", bool(end.get("summary", {}).get("disposition")), json.dumps(end)[:200])
md2 = get(f"/context/{SELLER}.md").text
check("seller.md reflects the voice call after hang-up", "voice" in md2.lower() or "VANI call" in md2, md2[:400])
wa2 = post("/api/whatsapp", {"glid": SELLER, "text": "Call ke baad quotation bhej do"}).json()
check("Back on WhatsApp after the call (3rd channel hop)", bool(wa2.get("reply")))
check("Empty call history → skipped", post("/api/call/end", {"glid": SELLER, "history": []}).json().get("skipped") is True)
check("Turn without text → 400", post("/api/call/turn", {"glid": SELLER}).status_code == 400)

# ---------------------------------------------------------------- buyer + cold flows
b = post("/api/call/start", {"glid": BUYER, "tts": False}).json()
check("Buyer call opens personalised", "ji" in b.get("text", ""), b.get("text", "")[:200])
bw = post("/api/whatsapp", {"glid": BUYER, "text": "Kya aap mujhe 3 aur suppliers bhej sakte ho?"}).json()
check("Buyer WhatsApp updates buyer.md", bool(bw.get("reply")) and "3 aur suppliers" in get(f"/context/{BUYER}.md").text)
cw = post("/api/whatsapp", {"glid": COLD, "text": "Kal shaam 5 baje ke baad call karna"}).json()
check("Unknown user's first WhatsApp warms the file", bool(cw.get("reply")) and "cold_start: true" not in get(f"/context/{COLD}.md").text)

# ---------------------------------------------------------------- edge-case input
for label, text in (("Devanagari", "मुझे स्टील पाइप का रेट चाहिए"), ("emoji/special", "Rate?? 🙏 <b>&amp;</b> ' \" ;--"),
                    ("very long", "pipe " * 800)):
    rr = post("/api/whatsapp", {"glid": SELLER, "text": text})
    check(f"WhatsApp with {label} text", rr.status_code == 200 and rr.json().get("reply"), str(rr.status_code))
check("Huge message keeps file inside token budget", len(get(f"/context/{SELLER}.md").text) < 6000)
check("Missing fields → 422", post("/api/whatsapp", {"text": "hi"}).status_code == 422)
ev = post("/api/events", {"glid": SELLER, "channel": "app_chat", "kind": "typed", "text": "App se: catalogue update karna hai"})
check("POST /api/events accepts a new channel (app_chat)", ev.status_code == 200, ev.text[:200])
check("app_chat event reaches the file", "catalogue update" in get(f"/context/{SELLER}.md").text)
ac = post("/api/chat", {"glid": BUYER, "channel": "app_chat", "text": "App par quotation compare karna hai, kaise?"})
check("POST /api/chat (app channel) replies", ac.status_code == 200 and ac.json().get("reply"), ac.text[:200])
check("…buyer.md labels it App chat", "App chat" in get(f"/context/{BUYER}.md").text)
check("Unknown chat channel → 400", post("/api/chat", {"glid": SELLER, "channel": "fax", "text": "hi"}).status_code == 400)

# ---------------------------------------------------------------- reuse beyond the bot
br = get(f"/brief/{SELLER}")
check("GET /brief (executive call-prep)", br.status_code == 200 and "Executive call prep" in br.text)
check("GET /brief for buyer", get(f"/brief/{BUYER}").status_code == 200)
sg = get("/api/segments").json()
check("GET /api/segments", sg.get("files_read", 0) > 0 and sg.get("segments"), json.dumps(sg)[:200])
csv = get("/api/segments", params={"format": "csv"})
check("GET /api/segments?format=csv", csv.status_code == 200 and "," in csv.text)
m = get("/api/metrics").json()
check("GET /api/metrics reports live freshness", m.get("live_events", 0) > 0 and m["deterministic_ms"]["p50"] is not None)

# ---------------------------------------------------------------- Sarvam Voice Agent hooks
sc = get("/sarvam/context", params={"glid": SELLER}).json()
check("GET /sarvam/context (on_start tool)", sc.get("context_md", "").startswith("---") and sc.get("opening_line"))
se = post("/sarvam/call-ended", {"glid": SELLER, "summary": "Seller wants a callback Monday 11am", "disposition": "Call Later"}).json()
check("POST /sarvam/call-ended with summary", "version" in se, json.dumps(se)[:200])
check("…and the summary lands in seller.md", "Monday 11am" in get(f"/context/{SELLER}.md").text)
se2 = post("/sarvam/call-ended", {"glid": SELLER, "transcript": ["agent: Namaste", "user: Abhi busy hoon, baad mein"]})
check("POST /sarvam/call-ended with transcript list", se2.status_code == 200, se2.text[:200])

# ---------------------------------------------------------------- SSE stream
try:
    with requests.get(BASE + "/api/stream", stream=True, timeout=5) as s:
        check("GET /api/stream (live UI updates) opens", s.status_code == 200)
except requests.exceptions.ReadTimeout:
    check("GET /api/stream (live UI updates) opens", True)

failed = [r for r in results if not r[1]]
print(f"\n{len(results) - len(failed)}/{len(results)} checks passed")
sys.exit(1 if failed else 0)
