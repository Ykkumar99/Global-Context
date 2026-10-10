"""Sarvam AI clients (LLM, TTS, STT) with graceful offline fallback.

* LLM : POST {base}/v1/chat/completions      (sarvam-105b)
* TTS : POST {base}/text-to-speech           (Bulbul v3, base64 WAV in "audios")
* STT : POST {base}/speech-to-text           (Saaras v4, multipart, mode=codemix)

If SARVAM_API_KEY is not set (or a call fails) the system keeps working:
LLM features fall back to an optional OpenAI-compatible endpoint, then to
deterministic templates; TTS/STT fall back to the browser's Web Speech APIs.
"""
from __future__ import annotations

import base64
import io
import json
import logging
import re
import threading
import time
import wave
from collections import deque
from concurrent.futures import ThreadPoolExecutor

import requests

from .config import get_config
from .pronounce import for_tts

log = logging.getLogger("gcx.sarvam")
_THINK = re.compile(r"<think>.*?</think>", re.S)


class _RateLimiter:
    """Sliding-window requests-per-minute guard, so we stay under the plan limit instead of collecting 429s.
    Starter plan: bulbul:v3 30/min, sarvam-105b 40/min, STT 60/min (docs.sarvam.ai → Rate limits)."""

    def __init__(self, rpm: int):
        self.rpm = max(1, int(rpm))
        self.ts: deque = deque()
        self.lock = threading.Lock()

    def _prune(self, now: float) -> None:
        while self.ts and now - self.ts[0] >= 60:
            self.ts.popleft()

    def free(self) -> int:
        with self.lock:
            self._prune(time.monotonic())
            return self.rpm - len(self.ts)

    def acquire(self, wait: float) -> bool:
        """Take one slot, waiting up to ``wait`` seconds; False = would exceed the limit."""
        end = time.monotonic() + wait
        while True:
            with self.lock:
                now = time.monotonic()
                self._prune(now)
                if len(self.ts) < self.rpm:
                    self.ts.append(now)
                    return True
                retry_in = 60 - (now - self.ts[0]) + 0.01
            if now + retry_in > end:
                return False
            time.sleep(min(retry_in, 0.25))

    def saturate(self) -> None:
        """The server said 429: assume this minute's budget is spent."""
        with self.lock:
            now = time.monotonic()
            while len(self.ts) < self.rpm:
                self.ts.append(now)


class Sarvam:
    def __init__(self):
        self.cfg = get_config()
        s = self.cfg.sarvam or {}
        self.base = (s.get("base_url") or "https://api.sarvam.ai").rstrip("/")
        self.s = s
        self.key = self.cfg.sarvam_key
        self.timeout = s.get("timeout_sec", 20)
        self.last_error: str | None = None
        self.stats = {"llm_calls": 0, "llm_ms": 0.0, "tts_calls": 0, "tts_ms": 0.0, "stt_calls": 0, "stt_ms": 0.0,
                      "rate_limited": 0}
        # a little under the Starter limits (105b 40/min, bulbul:v3 30/min, STT 60/min) for headroom
        self.limits = {"llm": _RateLimiter(s.get("llm_rpm", 35)), "tts": _RateLimiter(s.get("tts_rpm", 27)),
                       "stt": _RateLimiter(s.get("stt_rpm", 55))}
        # batch=True (evaluation jobs): wait for quota and retry 429s instead of falling back, so a benchmark
        # never silently mixes offline answers into "Sarvam" results
        self.batch = False

    def budget(self, kind: str) -> int:
        """Requests still free this minute — background work (pre-warm, AI polish) only runs when there is spare."""
        return self.limits[kind].free()

    # ------------------------------------------------------------ status
    @property
    def enabled(self) -> bool:
        return bool(self.key)

    def mode(self) -> dict:
        fb = self.cfg.fallback_llm or {}
        return {
            "llm": "sarvam" if self.key else ("fallback" if fb.get("base_url") and self.cfg.fallback_key else "offline"),
            "tts": "sarvam" if self.key else "browser",
            "stt": "sarvam" if self.key else "browser",
            "last_error": self.last_error,
        }

    def _headers(self) -> dict:
        return {"api-subscription-key": self.key or "", "Authorization": f"Bearer {self.key or ''}"}

    # --------------------------------------------------------------- LLM
    def chat(self, messages: list[dict], max_tokens: int = 400, temperature: float = 0.3,
             json_mode: bool = False) -> str | None:
        if self.key:
            body = {"model": self.s.get("chat_model", "sarvam-105b"), "messages": messages,
                    "max_tokens": max_tokens, "temperature": temperature, "reasoning_effort": None}
            if json_mode:
                body["response_format"] = {"type": "json_object"}
            out = self._post_chat(f"{self.base}/v1/chat/completions", body, self._headers())
            if out is None and json_mode and "429" not in (self.last_error or ""):  # model rejected response_format
                body.pop("response_format", None)
                out = self._post_chat(f"{self.base}/v1/chat/completions", body, self._headers())
            if out is not None:
                return out
        fb = self.cfg.fallback_llm or {}
        if fb.get("base_url") and self.cfg.fallback_key:
            body = {"model": fb.get("model"), "messages": messages, "max_tokens": max_tokens,
                    "temperature": temperature}
            return self._post_chat(fb["base_url"].rstrip("/") + "/chat/completions", body,
                                   {"Authorization": f"Bearer {self.cfg.fallback_key}"})
        return None

    def _post_chat(self, url: str, body: dict, headers: dict) -> str | None:
        sarvam = url.startswith(self.base)
        if sarvam and not self.limits["llm"].acquire(wait=65 if self.batch else 8):
            self.last_error = "LLM: local rate limit reached (sarvam-105b 40/min) — using fallback"
            self.stats["rate_limited"] += 1
            return None
        t0 = time.perf_counter()
        try:
            r = requests.post(url, json=body, headers=headers, timeout=self.timeout)
            for _ in range(4 if (sarvam and self.batch) else 0):
                if r.status_code != 429:
                    break
                self.stats["rate_limited"] += 1
                time.sleep(20)
                r = requests.post(url, json=body, headers=headers, timeout=self.timeout)
            if sarvam and r.status_code == 429:
                self.limits["llm"].saturate()
                self.stats["rate_limited"] += 1
            r.raise_for_status()
            msg = r.json()["choices"][0]["message"]
            text = _THINK.sub("", msg.get("content") or "").strip()
            self.stats["llm_calls"] += 1
            self.stats["llm_ms"] += (time.perf_counter() - t0) * 1000
            return text or None
        except Exception as e:  # network, auth, schema
            detail = getattr(getattr(e, "response", None), "text", "")[:200]
            self.last_error = f"LLM: {e} {detail}".strip()
            log.warning(self.last_error)
            return None

    def chat_json(self, messages: list[dict], max_tokens: int = 500) -> dict | None:
        txt = self.chat(messages, max_tokens=max_tokens, temperature=0.2, json_mode=True)
        if not txt:
            return None
        m = re.search(r"\{.*\}", txt, re.S)
        try:
            return json.loads(m.group(0) if m else txt)
        except (ValueError, AttributeError):
            self.last_error = f"LLM returned non-JSON: {txt[:120]}"
            return None

    # --------------------------------------------------------------- TTS
    _SENT = re.compile(r"(?<=[.?!।|])\s+")

    @classmethod
    def speech_chunks(cls, text: str) -> list[str]:
        """At most two chunks, split only at a sentence end: a clause split ("Ji, main ... ,") breaks the speaker's
        intonation and sounded robotic in a real test call. Short replies are one request; longer ones are first
        sentence + rest, synthesised in parallel so the first sentence can start early (2 TTS requests/reply)."""
        text = text.strip()
        if len(text) <= 90:
            return [text] if text else []
        sents = [x for x in cls._SENT.split(text) if x.strip()]
        if len(sents) < 2:
            return [text]
        head = sents[0]
        rest = text[len(head):].strip()
        return [head, rest] if rest else [head]

    def tts(self, text: str, speaker: str | None = None, language: str | None = None,
            pace: float | None = None) -> bytes | None:
        """Synthesise sentences in parallel and join them — Bulbul time grows with length, so a 2-sentence
        reply comes back in ~the time of its longest sentence instead of the sum (~40% faster in tests)."""
        if not self.key or not text.strip():
            return None
        lang = language or self.s.get("tts_language", "hi-IN")
        # respell brand and domain words in this language's own script before chunking, so a term split
        # across two chunks is still replaced consistently
        text = for_tts(text, lang)
        parts = self.speech_chunks(text)
        if len(parts) < 2:
            return self._tts_one(text, speaker, language, pace)
        with ThreadPoolExecutor(min(6, len(parts))) as ex:
            outs = list(ex.map(lambda p: self._tts_one(p, speaker, language, pace), parts))
        if any(o is None for o in outs):
            return self._tts_one(text, speaker, language, pace)
        try:
            return _join_wav(outs)
        except (wave.Error, EOFError):
            return self._tts_one(text, speaker, language, pace)

    def _voice(self, lang: str, speaker: str | None) -> tuple[str, str]:
        """(model, speaker) for a language: Bulbul v4-flash conversational voices where one exists (more natural
        and faster), else the v3 voice. Hindi and English share one speaker so a language switch keeps the person."""
        voices = self.s.get("tts_voices") or {}
        if speaker:
            return self.s.get("tts_fallback_model", "bulbul:v3"), speaker.lower()
        if lang in voices:
            return self.s.get("tts_model", "bulbul:v4-flash"), voices[lang]
        return self.s.get("tts_fallback_model", "bulbul:v3"), self.s.get("tts_speaker", "priya")

    def _tts_one(self, text: str, speaker: str | None = None, language: str | None = None,
                 pace: float | None = None) -> bytes | None:
        lang = language or self.s.get("tts_language", "hi-IN")
        model, spk = self._voice(lang, speaker)
        plan = [(model, spk)]
        if model != self.s.get("tts_fallback_model", "bulbul:v3"):  # v4 voice rejected -> same text on v3
            plan.append((self.s.get("tts_fallback_model", "bulbul:v3"), self.s.get("tts_speaker", "priya")))
        t0 = time.perf_counter()
        for model, spk in plan:
            body = {"text": text[:2400], "speaker": spk, "model": model, "target_language_code": lang,
                    "pace": pace or self.s.get("tts_pace", 1.0)}
            if not self.limits["tts"].acquire(wait=4):
                self.last_error = "TTS: local rate limit reached — browser voice used"
                self.stats["rate_limited"] += 1
                return None
            try:
                r = requests.post(f"{self.base}/text-to-speech", json=body, headers=self._headers(),
                                  timeout=self.timeout)
                if r.status_code == 429:  # a retry would only burn more quota
                    self.limits["tts"].saturate()
                    self.stats["rate_limited"] += 1
                    self.last_error = f"TTS 429: {r.text[:160]}"
                    return None
                if r.status_code >= 400:
                    self.last_error = f"TTS {r.status_code} ({model}/{spk}): {r.text[:200]}"
                    continue
                audios = r.json().get("audios") or []
                if audios:
                    self.stats["tts_calls"] += 1
                    self.stats["tts_ms"] += (time.perf_counter() - t0) * 1000
                    return base64.b64decode("".join(audios))
            except Exception as e:
                self.last_error = f"TTS: {e}"
        log.warning(self.last_error)
        return None

    # --------------------------------------------------------------- STT
    def stt(self, audio: bytes, filename: str = "audio.webm", mime: str = "audio/webm") -> dict | None:
        if not self.key or not audio:
            return None
        if not self.limits["stt"].acquire(wait=4):
            self.last_error = "STT: local rate limit reached"
            return None
        t0 = time.perf_counter()
        try:
            r = requests.post(
                f"{self.base}/speech-to-text",
                headers={"api-subscription-key": self.key},
                files={"file": (filename, audio, mime.split(";")[0].strip())},  # "audio/wav;codecs=1" → "audio/wav"
                data={"model": self.s.get("stt_model", "saaras:v4"), "mode": self.s.get("stt_mode", "codemix")},
                timeout=self.timeout,
            )
            r.raise_for_status()
            j = r.json()
            self.stats["stt_calls"] += 1
            self.stats["stt_ms"] += (time.perf_counter() - t0) * 1000
            return {"transcript": j.get("transcript", ""), "language_code": j.get("language_code")}
        except Exception as e:
            detail = getattr(getattr(e, "response", None), "text", "")[:200]
            self.last_error = f"STT: {e} {detail}".strip()
            log.warning(self.last_error)
            return None


_CLIENT: Sarvam | None = None


def _join_wav(chunks: list[bytes]) -> bytes:
    """Concatenate WAV files that share one format (Bulbul returns 16-bit mono PCM)."""
    params, frames = None, []
    for c in chunks:
        with wave.open(io.BytesIO(c)) as w:
            if params is None:
                params = w.getparams()
            elif w.getparams()[:3] != params[:3]:
                raise wave.Error("mismatched WAV formats")
            frames.append(w.readframes(w.getnframes()))
    out = io.BytesIO()
    with wave.open(out, "wb") as w:
        w.setparams(params)
        for f in frames:
            w.writeframes(f)
    return out.getvalue()


def client() -> Sarvam:
    global _CLIENT
    if _CLIENT is None:
        _CLIENT = Sarvam()
    return _CLIENT
