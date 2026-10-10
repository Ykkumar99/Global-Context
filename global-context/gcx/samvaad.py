"""Real phone calls through Sarvam Voice Agents (Samvaad) — Instant Outbound + its completion webhook.

    place_call(glid, phone)   POST /outbounds/v1/orgs/{org}/workspaces/{ws}/outbounds
                              Payal dials the phone with the seller's memory file already loaded as agent variables.
    handle_webhook(payload)   Sarvam POSTs the outcome after the attempt ends (connected / no_answer / busy / failed).
                              A connected call is summarised and written back to the same memory file, so WhatsApp
                              (or the next call) resumes from it.

Docs: https://docs.sarvam.ai/conversations/api/instant-outbound/create
      https://docs.sarvam.ai/conversations/api/instant-outbound/webhook-payload

The agent's own on_end ``save_call`` tool would write the same call back a second time, so while an outbound
attempt is pending for a GLID the webhook owns the write-back and ``/sarvam/call-ended`` skips it
(see :func:`webhook_owns`).
"""
from __future__ import annotations

import os
import re
import threading
import time

import requests

from .config import get_config

OUTBOUND_URL = "https://apps.sarvam.ai/api/outbounds/v1/orgs/{org_id}/workspaces/{workspace_id}/outbounds"
WEBHOOK_PATH = "/sarvam/outbound-webhook"
PENDING_TTL = 20 * 60  # a webhook later than this is treated as lost; the on_end hook writes back again

# app_overrides.initial_language_name accepts these names only
SAMVAAD_LANG = {"hi-IN": "Hindi", "en-IN": "English", "gu-IN": "Gujarati", "mr-IN": "Marathi", "ta-IN": "Tamil",
                "te-IN": "Telugu", "kn-IN": "Kannada", "ml-IN": "Malayalam", "bn-IN": "Bengali", "pa-IN": "Punjabi",
                "od-IN": "Odia", "as-IN": "Assamese"}

_lock = threading.Lock()
META_KEY = "outbound_attempts"  # attempt_id -> {glid, phone, placed_at, status, ...}, newest last. Kept in the
KEEP = 50                       # SQLite store so `python -m gcx call` and the server see the same pending calls.


def _load(store) -> dict[str, dict]:
    return store.get_meta(META_KEY, {}) or {}


def _save(store, attempts: dict[str, dict]) -> None:
    store.set_meta(META_KEY, dict(list(attempts.items())[-KEEP:]))


class OutboundError(RuntimeError):
    def __init__(self, msg: str, status: int = 400):
        super().__init__(msg)
        self.status = status


def settings() -> dict:
    cfg = get_config()
    s = dict(cfg.samvaad or {})
    pub = os.environ.get("GCX_PUBLIC_URL") or s.get("public_url") or ""
    return {"org_id": s.get("org_id") or "", "workspace_id": s.get("workspace_id") or "",
            "app_id": s.get("app_id") or "", "app_version": s.get("app_version"),
            "connection_id": os.environ.get("GCX_SAMVAAD_CONNECTION_ID") or s.get("connection_id") or "",
            "agent_phone_number": os.environ.get("GCX_SAMVAAD_AGENT_PHONE_NUMBER") or s.get("agent_phone_number") or "",
            "public_url": pub.rstrip("/"), "key": cfg.samvaad_key or ""}


def status() -> dict:
    """What is configured (never the key itself) — shown in the UI and /api/status."""
    s = settings()
    missing = [k for k in ("key", "org_id", "workspace_id", "app_id", "app_version", "connection_id",
                           "agent_phone_number") if not s[k]]
    return {"ready": not missing, "missing": missing, "webhook": bool(s["public_url"]),
            "agent_phone_number": s["agent_phone_number"]}


def normalise_phone(raw: str) -> str:
    """Accepts 98xxxxxxxx, 098xxxxxxxx, 9198xxxxxxxx or +9198xxxxxxxx → E.164 (+91 assumed for 10 digits)."""
    digits = re.sub(r"\D", "", raw or "")
    if (raw or "").strip().startswith("+") and 8 <= len(digits) <= 15:
        return "+" + digits
    if len(digits) == 11 and digits.startswith("0"):
        digits = digits[1:]
    if len(digits) == 10 and digits[0] in "6789":
        return "+91" + digits
    if len(digits) == 12 and digits.startswith("91"):
        return "+" + digits
    raise OutboundError(f"Not a valid phone number: {raw!r} (use a 10-digit Indian mobile or +<country><number>)")


def webhook_url(s: dict) -> str | None:
    if not s["public_url"]:
        return None
    token = os.environ.get("GCX_TUNNEL_TOKEN", "")
    return s["public_url"] + WEBHOOK_PATH + (f"?token={token}" if token else "")


def build_request(glid: int, phone: str, ctx: dict, s: dict, lang: str | None = None) -> dict:
    """The OutboundRequest body. ``ctx`` = {context_md, opening_line, language} from the memory file.

    Variables match the agent's declared input variables (glid, context, opening, language), so the call is
    personalised even if the agent's on_start ``load_context`` tool cannot reach the tunnel."""
    lang = lang or ctx.get("language") or "hi-IN"
    app_config = {
        "app_id": s["app_id"],
        "app_version": int(s["app_version"]),
        "connection_config": {"connection_id": s["connection_id"], "agent_phone_number": s["agent_phone_number"]},
        "agent_variables": {"glid": str(glid), "context": ctx.get("context_md", ""),
                            "opening": ctx.get("opening_line", ""), "language": lang},
    }
    if SAMVAAD_LANG.get(lang):
        app_config["app_overrides"] = {"initial_language_name": SAMVAAD_LANG[lang]}
    body = {"app_config": app_config, "user_config": {"user_phone_number": phone}}
    hook = webhook_url(s)
    if hook:
        body["webhook_config"] = {"url": hook, "metadata": {"glid": glid, "source": "global-context"}}
    return body


def place_call(store, glid: int, phone: str, ctx: dict, lang: str | None = None, timeout: float = 15) -> dict:
    s = settings()
    st = status()
    if not st["ready"]:
        raise OutboundError("Phone calls not configured — missing: " + ", ".join(st["missing"]) +
                            " (config.yaml → samvaad, key in .env as SARVAM_SAMVAAD_API_KEY)", 503)
    phone = normalise_phone(phone)
    body = build_request(glid, phone, ctx, s, lang)
    url = OUTBOUND_URL.format(org_id=s["org_id"], workspace_id=s["workspace_id"])
    try:
        r = requests.post(url, json=body, headers={"X-API-Key": s["key"], "Content-Type": "application/json"},
                          timeout=timeout)
    except requests.RequestException as e:
        raise OutboundError(f"Sarvam outbound API unreachable: {e}", 502)
    if r.status_code >= 400:
        detail = r.text[:400]
        try:
            j = r.json()
            detail = j.get("detail", j) if isinstance(j, dict) else j
        except ValueError:
            pass
        raise OutboundError(f"Sarvam outbound API {r.status_code}: {detail}", 502 if r.status_code >= 500 else 400)
    attempt_id = (r.json() or {}).get("attempt_id")
    if not attempt_id:
        raise OutboundError(f"Sarvam outbound API returned no attempt_id: {r.text[:200]}", 502)
    rec = {"attempt_id": attempt_id, "glid": glid, "phone": _mask(phone), "placed_at": time.time(),
           "status": "dialing", "webhook": bool(body.get("webhook_config"))}
    with _lock:
        a = _load(store)
        a[attempt_id] = rec
        _save(store, a)
    return dict(rec)


def webhook_owns(store, glid: int) -> bool:
    """True while an outbound attempt for this GLID is waiting for its webhook (which will do the write-back)."""
    now = time.time()
    return any(a.get("glid") == glid and a.get("webhook") and a.get("status") == "dialing"
               and now - a.get("placed_at", 0) < PENDING_TTL for a in _load(store).values())


def attempts(store, limit: int = 20) -> list[dict]:
    return list(_load(store).values())[-limit:][::-1]


def transcript_to_history(items: list | None) -> list[dict]:
    hist = []
    for t in items or []:
        if not isinstance(t, dict):
            continue
        text = str(t.get("en_text") or t.get("text") or t.get("content") or "").strip()
        if text:
            hist.append({"who": "bot" if str(t.get("role", "")).lower() in {"agent", "bot", "assistant"} else "user",
                         "text": text})
    return hist


def record_result(store, payload: dict) -> tuple[dict | None, int | None, bool]:
    """Updates the attempt registry from a webhook payload → (attempt record, glid, first delivery?).

    Webhooks can be retried; only the first delivery of an attempt_id should write to memory."""
    aid = payload.get("attempt_id")
    meta = ((payload.get("webhook_config") or {}).get("metadata") or {})
    with _lock:
        a = _load(store)
        rec = a.get(aid)
        glid = (rec or {}).get("glid") or _int(meta.get("glid"))
        if rec is None and aid:  # placed elsewhere / registry lost: rebuild from the echoed metadata
            rec = a[aid] = {"attempt_id": aid, "glid": glid, "phone": "", "placed_at": time.time(),
                                    "webhook": True}
        first = rec is not None and not rec.get("ended_at")
        if first:
            rec.update(status=payload.get("status") or "unknown", duration=payload.get("duration"),
                       interaction_id=payload.get("interaction_id"), failure_reason=payload.get("failure_reason"),
                       ended_at=time.time())
            _save(store, a)
    return (dict(rec) if rec else None), glid, first


def _int(v) -> int | None:
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def _mask(phone: str) -> str:
    return phone[:-6] + "xxxx" + phone[-2:] if len(phone) > 8 else phone
