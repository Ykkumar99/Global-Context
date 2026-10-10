"""FastAPI service: context API for any consumer + the cross-channel demo.

Context API (reusable beyond the bot)
  GET  /context/{glid}.md            the file, text/markdown (what the bot loads)
  GET  /api/context/{glid}           JSON: md, version, tokens, sections
  POST /api/events                   push new activity -> incremental refresh
  GET  /api/metrics                  freshness + build stats
  GET  /api/stream                   server-sent events: live file updates

Sarvam Voice Agent hooks (configure as HTTPS tools on the agent)
  GET  /sarvam/context?glid=...      on_start: returns context + opening line
  POST /sarvam/call-ended            on_end: writes the call outcome back

Demo
  /                                   3-pane UI (WhatsApp · live seller.md · voice call)
"""
from __future__ import annotations

import asyncio
import base64
import hmac
import json
import os
import re
import threading
import time
from collections import deque
from contextlib import asynccontextmanager

import requests
from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, PlainTextResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import __version__
from . import seller_sections as S
from .agent import MOOD_PACE, Agent, detect_lang, detect_mood, requested_lang
from .config import ROOT, get_config
from .engine import ContextEngine
from . import samvaad
from .sarvam import client as sarvam_client
from .textutil import clean

cfg = get_config()
engine = ContextEngine()
agent = Agent(engine)
sarvam = sarvam_client()

_loop: asyncio.AbstractEventLoop | None = None


@asynccontextmanager
async def lifespan(_app):
    global _loop
    _loop = asyncio.get_running_loop()
    if engine.store.event_count() == 0:
        print("  ! Store is empty — run `python -m gcx setup` first.")
    yield


app = FastAPI(title="Global Context — VANI memory layer", version=__version__, lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
WEB = ROOT / "web"
app.mount("/static", StaticFiles(directory=WEB), name="static")


@app.middleware("http")
async def tunnel_guard(request: Request, call_next):
    """Requests arriving through a public tunnel (Cloudflare adds cf-connecting-ip) may only reach the Sarvam
    Voice Agent hooks, and only with GCX_TUNNEL_TOKEN — so nobody on the internet can browse the demo data or
    spend the team's Sarvam credits through the other routes. Local use is unaffected."""
    if request.headers.get("cf-connecting-ip"):
        token = os.environ.get("GCX_TUNNEL_TOKEN", "")
        given = request.query_params.get("token") or request.headers.get("x-gcx-token", "")
        if not (request.url.path.startswith("/sarvam/") and token and hmac.compare_digest(given, token)):
            return JSONResponse({"error": "not available through the public tunnel"}, status_code=403)
    return await call_next(request)


@app.middleware("http")
async def no_stale_ui(request: Request, call_next):
    """Demo UI files change between builds — always revalidate so nobody sees an old app.js."""
    resp = await call_next(request)
    if request.url.path == "/" or request.url.path.startswith("/static/"):
        resp.headers["Cache-Control"] = "no-cache"
    return resp

FEATURED_PATH = ROOT / "data" / "demo" / "featured.json"

# --------------------------------------------------------------- live push
_subscribers: set[asyncio.Queue] = set()
_loop: asyncio.AbstractEventLoop | None = None


def _push(glid: int, payload: dict) -> None:
    if _loop is None:
        return
    data = json.dumps({k: v for k, v in payload.items() if k != "dropped"}, default=str)
    for q in list(_subscribers):
        _loop.call_soon_threadsafe(q.put_nowait, data)


engine.listeners.append(_push)


# ------------------------------------------- opener pre-warm (voice latency)
# The opener depends only on the file, so its text + Bulbul audio are prepared in the background as soon as a user
# is opened or their file changes. "Start call" then plays immediately instead of waiting ~5 s for LLM + TTS.
_open_cache: dict[tuple[int, bool], tuple[int, dict, str | None]] = {}
_open_locks: dict[tuple[int, bool], threading.Lock] = {}
_recent: deque = deque(maxlen=20)  # users opened recently — only these are pre-warmed on file changes


def _opening_with_audio(glid: int, use_context: bool, tts: bool = True) -> tuple[dict, str | None, bool]:
    key = (glid, use_context)
    lock = _open_locks.setdefault(key, threading.Lock())
    with lock:  # a call that starts while the pre-warm is running waits for it instead of doing the work twice
        h = hash(engine.get(glid)["md"]) if use_context else 0
        hit = _open_cache.get(key)
        if hit and hit[0] == h and (hit[2] or not tts):
            return hit[1], hit[2], True
        op = agent.opening(glid, use_context)
        audio = _tts_b64(op["text"], op["lang"]) if tts else None
        _open_cache[key] = (h, op, audio)
        return op, audio, False


def _prewarm(glid: int) -> None:
    if sarvam.mode()["tts"] != "sarvam" or sarvam.budget("tts") < 10:
        return  # offline (opener is instant anyway) or TTS quota needed for live calls (bulbul:v3 30/min)

    def run():
        try:  # memory-on opener only; the memory-off comparison is generated on demand
            _opening_with_audio(glid, True)
        except Exception:  # pre-warm is best-effort; the call path recomputes on demand
            pass
    threading.Thread(target=run, daemon=True).start()


def _prewarm_on_change(glid: int, payload: dict) -> None:
    if glid in _recent and payload.get("type") == "doc":
        _prewarm(glid)


engine.listeners.append(_prewarm_on_change)


@app.get("/api/stream")
async def stream(request: Request):
    q: asyncio.Queue = asyncio.Queue()
    _subscribers.add(q)

    async def gen():
        try:
            yield "retry: 2000\n\n"
            while not await request.is_disconnected():
                try:
                    msg = await asyncio.wait_for(q.get(), timeout=15)
                    yield f"data: {msg}\n\n"
                except asyncio.TimeoutError:
                    yield ": ping\n\n"
        finally:
            _subscribers.discard(q)

    return StreamingResponse(gen(), media_type="text/event-stream")


# ---------------------------------------------------------------- helpers
def _need(glid: int) -> None:
    """Unknown GLIDs are allowed: they get a cold-start file, and their first event creates a profile."""
    if glid <= 0:
        raise HTTPException(400, "GLID must be a positive integer")


def _tts_b64(text: str, lang: str | None = None, pace: float | None = None) -> str | None:
    audio = sarvam.tts(text, language=lang, pace=pace)
    return base64.b64encode(audio).decode() if audio else None


COLD_DEMO_GLID = 999000001


def _label(glid: int) -> dict:
    prof = engine.store.profile(glid)
    if prof is None or prof[1].get("new_user"):
        return {"glid": glid, "role": prof[0] if prof else "unknown", "name": "New contact (no history)", "city": "",
                "what": "cold start"}
    role, p = prof
    if role == "seller":
        return {"glid": glid, "role": role, "name": clean(p.get("company_name")), "city": clean(p.get("seller_city")),
                "what": clean(p.get("top_category_1"))}
    k = p.get("kycdetails") or {}
    return {"glid": glid, "role": role, "name": clean(k.get("customer_name")) or clean(k.get("company_name")),
            "city": clean(k.get("city")), "what": clean(k.get("company_name"))}


# -------------------------------------------------------------- core API
@app.get("/")
def index():
    return FileResponse(WEB / "index.html")


@app.get("/api/status")
def status():
    stats = engine.store.get_meta("ingest_stats", {})
    return {"version": __version__, "modes": sarvam.mode(), "as_of": str(engine.now())[:19],
            "events": engine.store.event_count(), "ingest": stats, "token_budget": engine.budget,
            "sarvam_stats": sarvam.stats, "samvaad": samvaad_config()}


@app.get("/api/users")
def users(role: str | None = None, q: str | None = None, limit: int = 40):
    featured = json.loads(FEATURED_PATH.read_text()) if FEATURED_PATH.exists() else {}
    ids = [g for g in featured.get(role or "seller", []) if engine.role(g)] if not q else []
    if q:
        rows = engine.store.conn().execute(
            "SELECT glid FROM profiles WHERE (?1 IS NULL OR role=?1) AND (CAST(glid AS TEXT) LIKE ?2 OR data LIKE ?3) "
            "LIMIT ?4", (role, f"{q}%", f"%{q}%", limit)).fetchall()
        ids = [r[0] for r in rows]
    if len(ids) < limit and not q:
        ids += [g for g in engine.store.glids(role) if g not in ids][: limit - len(ids)]
    out = [_label(g) for g in ids[:limit]]
    if not q and (role in (None, "seller")):
        out.append(_label(COLD_DEMO_GLID))  # demo: a brand-new user with no history on any channel
    return out


@app.get("/context/{glid}.md", response_class=PlainTextResponse)
def context_md(glid: int):
    return PlainTextResponse(engine.get(glid)["md"], media_type="text/markdown; charset=utf-8")


@app.get("/api/context/{glid}")
def context_json(glid: int, rebuild: bool = False):
    if glid not in _recent:
        _recent.append(glid)
    _prewarm(glid)
    if engine.role(glid) is None:
        return {**engine.cold_doc(glid), "sections": {}, "label": _label(glid)}
    d = engine.build(glid) if rebuild else engine.get(glid)
    secs = {k: json.loads(v) for k, v in engine.store.sections(glid).items() if not k.startswith("_")}
    return {**{k: v for k, v in d.items() if k != "dropped"}, "sections": secs, "label": _label(glid)}


class EventIn(BaseModel):
    glid: int
    channel: str = Field(..., examples=["wa_chat"])
    kind: str | None = "typed"
    text: str | None = None
    meta: dict | None = None


@app.post("/api/events")
def push_event(e: EventIn):
    _need(e.glid)
    d = engine.on_event(e.glid, e.channel, e.kind, e.text, {**(e.meta or {}), "live": 1})
    return {k: v for k, v in d.items() if k != "dropped"}


@app.get("/api/metrics")
def metrics():
    rows = engine.store.freshness_rows()
    det = [(r["doc_at"] - r["received_at"]) * 1000 for r in rows if r["doc_at"] and r["received_at"]]
    llm = [(r["llm_at"] - r["received_at"]) * 1000 for r in rows if r["llm_at"] and r["received_at"]]

    def pctl(xs, p):
        return round(sorted(xs)[min(len(xs) - 1, int(p * len(xs)))], 1) if xs else None

    return {"live_events": len(rows),
            "deterministic_ms": {"p50": pctl(det, .5), "p95": pctl(det, .95)},
            "llm_enriched_ms": {"p50": pctl(llm, .5), "p95": pctl(llm, .95)},
            "sarvam": sarvam.stats, "modes": sarvam.mode()}


# ------------------------------------------------------ channels: WhatsApp
class ChatIn(BaseModel):
    glid: int
    text: str
    history: list[dict] = []
    use_context: bool = True
    channel: str = "wa_chat"  # wa_chat | app_chat | web_chat — all write to the same memory file


@app.post("/api/whatsapp")
@app.post("/api/chat")
def whatsapp(m: ChatIn):
    _need(m.glid)
    if m.channel not in S.CHAT_CHANNELS:
        raise HTTPException(400, f"channel must be one of {', '.join(S.CHAT_CHANNELS)}")
    t0 = time.time()
    doc = engine.on_event(m.glid, m.channel, "typed", m.text, {"live": 1, "intent": "live_demo"})
    r = agent.reply(m.glid, m.history, m.text, use_context=m.use_context, channel="whatsapp")
    engine.store.add_event(m.glid, engine.now(), "wa_bot", "reply", r["text"], {"live": 1}, live=1)
    return {"reply": r["text"], "engine": r["engine"], "freshness_ms": doc["freshness_ms"],
            "version": doc["version"], "ms": round((time.time() - t0) * 1000)}


# ---------------------------------------------------------- channels: voice
class CallIn(BaseModel):
    glid: int
    use_context: bool = True
    lang: str = "hi-IN"          # the language the call is in right now
    stt_lang: str | None = None  # speech-to-text's guess for this turn (only a hint)
    history: list[dict] = []
    text: str | None = None
    tts: bool = True
    engine: str | None = None    # "samvaad" when the browser call ran on Sarvam's real-time engine


# glid -> when the browser saved a Samvaad call itself; the agent's own save_call tool (via the tunnel, if it's up)
# reports the same call a moment later and must not write it twice
_SAMVAAD_SAVED: dict[int, float] = {}
SAMVAAD_DEDUPE_S = 180


@app.post("/api/call/start")
def call_start(c: CallIn):
    _need(c.glid)
    t0 = time.time()
    op, audio, cached = _opening_with_audio(c.glid, c.use_context, c.tts)
    return {**op, "audio": audio if c.tts else None, "ms": round((time.time() - t0) * 1000), "prewarmed": cached,
            "modes": sarvam.mode()}


@app.post("/api/call/turn")
def call_turn(c: CallIn):
    _need(c.glid)
    if not c.text:
        raise HTTPException(400, "text required (or use /api/call/turn-audio)")
    t0 = time.time()
    # follow the caller's language turn by turn, but never flip on one short or ambiguous turn; an explicit
    # request ("Gujarati mein baat karo") wins, a complaint ("Marathi mein kyun?") resets to what they speak
    asked = requested_lang(c.text)
    if asked == "back":
        lang = detect_lang(c.text, hint=c.stt_lang, current="hi-IN")
    else:
        lang = asked or detect_lang(c.text, hint=c.stt_lang or c.lang, current=c.lang)
    mood = detect_mood(c.text)               # and their mood: tone, length and speaking pace adapt
    r = agent.reply(c.glid, c.history, c.text, use_context=c.use_context, lang=lang, mood=mood)
    t1 = time.time()
    pace = MOOD_PACE.get(mood)
    audio = _tts_b64(r["text"], lang, pace) if c.tts else None
    return {"user_text": c.text, "text": r["text"], "end": r["end"], "engine": r["engine"], "audio": audio, "lang": lang,
            "mood": mood, "pace": pace,
            "llm_ms": round((t1 - t0) * 1000), "tts_ms": round((time.time() - t1) * 1000)}


@app.post("/api/call/turn-audio")
async def call_turn_audio(glid: int = Form(...), use_context: bool = Form(True), history: str = Form("[]"),
                          lang: str = Form("hi-IN"), tts: bool = Form(True), audio: UploadFile = File(...)):
    _need(glid)
    t0 = time.time()
    raw = await audio.read()
    stt = sarvam.stt(raw, audio.filename or "audio.webm", audio.content_type or "audio/webm")
    if not stt or not stt.get("transcript"):
        return JSONResponse({"error": "speech not recognised", "detail": sarvam.last_error}, status_code=422)
    t1 = time.time()
    res = call_turn(CallIn(glid=glid, use_context=use_context, history=json.loads(history), text=stt["transcript"],
                           lang=lang, stt_lang=stt.get("language_code"), tts=tts))
    res.update(stt_ms=round((t1 - t0) * 1000), language=stt.get("language_code"))
    return res


@app.post("/api/call/end")
def call_end(c: CallIn):
    _need(c.glid)
    if not c.history:
        return {"skipped": True}
    who = "Sarvam voice agent" if c.engine == "samvaad" else None
    out = agent.end_call(c.glid, c.history, who) if who else agent.end_call(c.glid, c.history)
    if who:
        _SAMVAAD_SAVED[c.glid] = time.time()
    d = out["doc"]
    return {"summary": out["summary"], "freshness_ms": d["freshness_ms"], "version": d["version"]}


@app.post("/api/tts")
def tts(body: dict):
    pace = body.get("pace")
    pace = min(1.3, max(0.8, float(pace))) if pace else None  # mood-adjusted speaking speed
    return {"audio": _tts_b64(str(body.get("text", "")), body.get("lang") or None, pace), "modes": sarvam.mode()}


# ------------------------------------------- non-bot consumers of the same files
@app.get("/brief/{glid}", response_class=HTMLResponse)
def exec_brief(glid: int):
    """Sales-executive call-prep page rendered from the seller.md / buyer.md file itself."""
    from .reuse import exec_brief_html
    return HTMLResponse(exec_brief_html(engine.get(glid)["md"]))


@app.get("/api/segments")
def campaign_segments(format: str = "json"):
    """WhatsApp-campaign / dialer segments computed by reading the .md files only."""
    from .reuse import SEGMENTS, files_from_dir, segments, segments_csv
    files = files_from_dir(cfg.path("out_dir") / "seller_md")
    if format == "csv":
        return Response(segments_csv(files), media_type="text/csv",
                        headers={"Content-Disposition": "attachment; filename=segments.csv"})
    seg = segments(files)
    return {"files_read": len(files),
            "segments": {k: {"description": SEGMENTS[k][0], "count": len(v), "sample": v[:10]} for k, v in seg.items()}}


# ------------------------------------------------- Sarvam Voice Agent hooks
_SENT = re.compile(r"(?<=[.?!।])\s+")


def _mid(s: str) -> str:
    """'Main IndiaMART…' → 'main IndiaMART…' mid-sentence, but leave names alone ('KPR Tempo…', 'IndiaMART…')."""
    return s[0].lower() + s[1:] if len(s) > 1 and s[0].isupper() and s[1].islower() else s


def split_greeting(text: str, lang: str) -> tuple[str, str]:
    """Samvaad never lets the caller interrupt the agent's greeting — caller audio is dropped until it ends — so a
    12-second memory opener left people talking into a dead line. Split it: a short hello the caller can answer
    (greeting), and the memory point (hook) for the agent's first normal, interruptible turn."""
    sents = [x for x in _SENT.split(text.strip()) if x]
    cut = next((i for i, x in enumerate(sents) if "IndiaMART" in x), -1)
    if cut < 0 or cut == len(sents) - 1:
        return text.strip(), ""
    greet, hook = sents[:cut + 1], " ".join(sents[cut + 1:])
    if lang == "hi-IN":
        ask = next((x for x in greet if x.rstrip().endswith("?")), None)
        if ask:  # "Namaste, kya meri baat X se ho rahi hai? Main … Payal …" → introduce first, then ask: it invites a reply
            intro = " ".join(x for x in greet if x is not ask).rstrip(".")
            first = re.sub(r"^(Namaste),?\s*", "", ask)
            return f"Namaste, {_mid(intro)} — {_mid(first)}", hook
        return " ".join(greet).rstrip(".") + " — kya abhi do minute baat ho sakti hai?", hook
    return " ".join(greet), hook


@app.get("/sarvam/context")
def sarvam_context(glid: int):
    d = engine.get(glid)
    op = agent.opening(glid, True)
    greeting, hook = split_greeting(op["text"], op["lang"])
    md = d["md"]
    if hook:  # the agent reads {context}: tell it what to raise once the caller answers the greeting
        md += ("\n\n## Your first point — say this right after they answer your greeting (in their language)\n"
               f"> {hook}\n")
    return {"glid": glid, "context_md": md, "opening_line": greeting, "first_point": hook, "language": op["lang"],
            "version": d["version"]}


class CallEnded(BaseModel):
    glid: int
    transcript: str | list | None = None
    disposition: str | None = None
    summary: str | None = None


@app.post("/sarvam/call-ended")
def sarvam_call_ended(c: CallEnded):
    _need(c.glid)
    if samvaad.webhook_owns(engine.store, c.glid):  # a phone call we placed: its outbound webhook writes the outcome back once
        return {"skipped": True, "reason": "outbound webhook will write this call back"}
    if time.time() - _SAMVAAD_SAVED.get(c.glid, 0) < SAMVAAD_DEDUPE_S:
        return {"skipped": True, "reason": "browser already saved this Samvaad call"}
    if c.summary:
        d = engine.on_event(c.glid, "voice_call", c.disposition or "General (talked)", c.summary,
                            {"agent": "Sarvam voice agent", "live": 1})
        return {"version": d["version"], "freshness_ms": d["freshness_ms"]}
    tr = c.transcript
    if isinstance(tr, str) and tr.strip().startswith("["):  # platforms sometimes send the list JSON-encoded
        try:
            tr = json.loads(tr)
        except ValueError:
            pass
    lines = tr if isinstance(tr, list) else str(tr or "").splitlines()
    hist = []
    for ln in lines:
        s = ln if isinstance(ln, str) else f"{ln.get('role', '')}: {ln.get('content', '')}"
        who = "bot" if s.lower().startswith(("agent", "assistant", "bot", "payal")) else "user"
        hist.append({"who": who, "text": s.split(":", 1)[-1].strip()})
    hist = [h for h in hist if h["text"]]
    if not any(h["who"] == "user" for h in hist):  # unanswered / empty call: nothing to remember
        return {"skipped": True, "reason": "no user speech in transcript"}
    out = agent.end_call(c.glid, hist, "Sarvam voice agent")
    return {"summary": out["summary"], "version": out["doc"]["version"]}


# --------------------------------------------------- Samvaad (real duplex call engine, browser SDK)
SAMVAAD_RUNTIME = "https://apps.sarvam.ai/api/app-runtime/"


def samvaad_config() -> dict:
    s = (cfg.samvaad or {})
    ids = {"org_id": s.get("org_id") or "", "workspace_id": s.get("workspace_id") or "", "app_id": s.get("app_id") or "",
           "app_version": s.get("app_version") or 1}
    return {**ids, "configured": bool(cfg.samvaad_key) and all([ids["org_id"], ids["workspace_id"], ids["app_id"]]),
            "phone": samvaad.status()}


# --------------------------------------- Samvaad Instant Outbound: Payal rings a real phone
class PhoneCallIn(BaseModel):
    glid: int
    phone: str
    lang: str | None = None  # override the language picked from the memory file (e.g. "gu-IN")


@app.post("/api/phone-call")
def phone_call(p: PhoneCallIn):
    """Local-only (the tunnel guard blocks it from outside): dial a phone with this GLID's memory loaded."""
    _need(p.glid)
    ctx = sarvam_context(p.glid)
    try:
        rec = samvaad.place_call(engine.store, p.glid, p.phone, ctx, lang=p.lang)
    except samvaad.OutboundError as e:
        raise HTTPException(e.status, str(e))
    _push(p.glid, {"type": "phone", "glid": p.glid, **rec})
    return {**rec, "opening_line": ctx["opening_line"], "version": ctx["version"]}


@app.get("/api/phone-calls")
def phone_calls(limit: int = 20):
    return {"status": samvaad.status(), "attempts": samvaad.attempts(engine.store, limit)}


@app.post(samvaad.WEBHOOK_PATH)
def sarvam_outbound_webhook(payload: dict):
    """Sarvam POSTs here after every Instant Outbound attempt. Reached through the tunnel with ?token=."""
    rec, glid, first = samvaad.record_result(engine.store, payload)
    out: dict = {"ok": True, "status": payload.get("status")}
    if not first:
        return {**out, "duplicate": True}
    if glid and payload.get("status") == "connected":
        hist = samvaad.transcript_to_history(payload.get("interaction_transcript"))
        if any(h["who"] == "user" for h in hist):
            meta = {k: payload.get(k) for k in ("attempt_id", "interaction_id") if payload.get(k)}
            if payload.get("duration") is not None:
                meta["duration"] = round(float(payload["duration"]))
            res = agent.end_call(glid, hist, "Sarvam phone call", meta)
            out.update(summary=res["summary"], version=res["doc"]["version"])
        else:
            out.update(skipped=True, reason="no user speech in transcript")
    # no_answer / busy / failed are shown live but not written into memory: a voice_call event there would be read
    # as "answered" and close the seller's open WhatsApp question
    if glid:
        _push(glid, {"type": "phone", "glid": glid, **(rec or {}), **{k: v for k, v in out.items() if k != "ok"}})
    return out


@app.get("/api/samvaad/{path:path}")
def samvaad_proxy(path: str, request: Request):
    """Proxies the one REST call the Samvaad browser SDK makes (mint a short-lived signed WebSocket URL) so the
    real Sarvam API key never reaches the browser. After this, the SDK talks to Sarvam directly for call audio —
    we never see or relay the media stream."""
    if not cfg.samvaad_key:
        raise HTTPException(503, "SARVAM_SAMVAAD_API_KEY not configured")
    try:
        r = requests.get(SAMVAAD_RUNTIME + path, params=dict(request.query_params),
                         headers={"X-API-Key": cfg.samvaad_key}, timeout=10)
    except requests.RequestException as e:
        raise HTTPException(502, f"Samvaad upstream error: {e}")
    return Response(content=r.content, status_code=r.status_code,
                    media_type=r.headers.get("content-type", "application/json"))
