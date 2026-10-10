"""Context engine: builds, incrementally refreshes and LLM-enriches seller.md / buyer.md.

Refresh logic
-------------
1. A new event arrives (API ``POST /events``, Kafka consumer, demo UI ...).
2. It is appended to the store and mapped to the sections that read its channel
   (``SECTION_DEPS``). Only those sections are recomputed; the rest come from the
   section cache. The file is re-rendered and written  -> *deterministic freshness*
   (milliseconds).
3. A background worker then asks the LLM to rewrite the free-text parts
   (open threads + opening line) from the fresh file -> *enriched freshness*
   (~1–3 s). Until it finishes, the deterministic version is served, so the bot
   never waits and never sees stale facts.
4. A nightly full rebuild (``python -m gcx build``) recomputes everything.
"""
from __future__ import annotations

import json
import logging
import queue
import threading
import time
from collections import Counter
from datetime import datetime, timedelta

from . import buyer_sections as B
from . import seller_sections as S
from .config import get_config
from .render import assemble, frontmatter
from .sarvam import client as sarvam_client
from .store import Clock, Store
from .textutil import ago, clean, counterpart_names, scrub_people

log = logging.getLogger("gcx.engine")

ALL_SELLER = [s for s in S.SECTION_ORDER if s != "opening"]


class ContextEngine:
    FULL_EVERY = timedelta(minutes=60)

    def __init__(self, store: Store | None = None, write_files: bool = True):
        self.cfg = get_config()
        self.store = store or Store()
        self.clock = Clock(self.store)
        self.budget = int(self.cfg.token_budget or 450)
        self.write_files = write_files
        self.out_dir = self.cfg.path("out_dir")
        self.llm = sarvam_client()
        self._q: queue.Queue = queue.Queue()
        self._pending: set[int] = set()
        self._worker: threading.Thread | None = None
        self.listeners: list = []  # callables(glid, payload) for live UI push

    # ------------------------------------------------------------- helpers
    def now(self) -> datetime:
        return self.clock.now()

    def role(self, glid: int) -> str | None:
        p = self.store.profile(glid)
        return p[0] if p else None

    def _source_counts(self, glid: int, now: datetime) -> dict[str, int]:
        since = (now - timedelta(days=90)).strftime("%Y-%m-%d %H:%M:%S")
        rows = self.store.conn().execute(
            "SELECT channel, COUNT(*) FROM events WHERE glid=? AND ts<=? AND ts>=? AND channel!='wa_bot' "
            "GROUP BY channel",
            (glid, now.strftime("%Y-%m-%d %H:%M:%S"), since)).fetchall()
        return {r[0]: r[1] for r in rows}

    # ---------------------------------------------------------------- seller
    def _seller_ctx(self, glid: int, now: datetime, strict_pit: bool, channels: set[str] | None) -> S.Ctx:
        prof = self.store.profile(glid)[1]
        evs = self.store.events(glid, now, channels=channels)
        return S.Ctx(glid, prof, evs, now, self.cfg, strict_pit=strict_pit)

    def build_seller(self, glid: int, now: datetime | None = None, only: set[str] | None = None,
                     strict_pit: bool = False, persist: bool = True) -> dict:
        t0 = time.perf_counter()
        now = now or self.now()
        names = [s for s in ALL_SELLER if (only is None or s in only)]
        needed = set().union(*(S.SECTION_DEPS[s] for s in names)) | S.SECTION_DEPS["threads"] | {"buylead"}
        needed.discard("profile")
        ctx = self._seller_ctx(glid, now, strict_pit, needed)
        fresh = {n: S.BUILDERS[n](ctx) for n in names}
        fresh["opening"] = [S.opening_line(ctx)]
        changed = []
        if persist and only is None:
            self.store.put_section(glid, "_full_at", json.dumps(now.isoformat()))
        if persist:
            for n, lines in fresh.items():
                if self.store.put_section(glid, n, json.dumps(lines, ensure_ascii=False)):
                    changed.append(n)
            if changed and any(n in changed for n in ("threads", "opening", "recent", "guardrails")):
                self.store.conn().execute("DELETE FROM sections WHERE glid=? AND section IN ('threads_llm','opening_llm')",
                                          (glid,))
                self.store.conn().commit()
            cached = {k: json.loads(v) for k, v in self.store.sections(glid).items()}
        else:
            cached = fresh
            changed = list(fresh)
        llm = "opening_llm" in cached
        secs = {k: v for k, v in cached.items() if not k.endswith("_llm") and not k.startswith("_")}
        if llm:
            secs["opening"] = cached["opening_llm"]
            if cached.get("threads_llm"):
                secs["threads"] = cached["threads_llm"]
        doc = self._render(glid, "seller", secs, S.SECTION_ORDER, S.SECTION_TITLES, now, llm, persist)
        doc.update(changed=changed, build_ms=(time.perf_counter() - t0) * 1000)
        return doc

    # ----------------------------------------------------------------- buyer
    def build_buyer(self, glid: int, now: datetime | None = None, persist: bool = True) -> dict:
        t0 = time.perf_counter()
        data = self.store.profile(glid)[1]
        secs, opening, meta = B.build_buyer_md_parts(glid, data)
        snap = meta["as_of"]
        now = max(now or self.now(), snap)
        live = self.store.events(glid, now, channels=[*S.CHAT_CHANNELS, "voice_call"])
        if live:  # live conversations happen after the API snapshot -> newest first
            lines = []
            for e in live[:3]:
                label = S.CHAT_LABEL.get(e["channel"], "Voice call")
                txt = clean(e.get("text"), 100)
                lines.append(f"{ago(e['ts'], now)} · {label}" + (f" ({e['kind']})" if e["kind"] else "") + f": {txt}")
            secs["recent"] = lines + secs.get("recent", [])
        secs["opening"] = [opening]
        cached = {k: json.loads(v) for k, v in self.store.sections(glid).items()} if persist else {}
        llm = False
        if cached.get("opening_llm") and cached.get("_llm_watermark") == [len(live)]:
            secs["opening"] = cached["opening_llm"]
            llm = True
        changed = []
        if persist:
            for n, lines in secs.items():
                if self.store.put_section(glid, n, json.dumps(lines, ensure_ascii=False)):
                    changed.append(n)
        doc = self._render(glid, "buyer", secs, B.BUYER_ORDER, B.BUYER_TITLES, now, llm, persist,
                           sources={"getContext": 1, **{k: v for k, v in Counter(e["channel"] for e in live).items()}})
        doc.update(changed=changed, build_ms=(time.perf_counter() - t0) * 1000, live_events=len(live))
        return doc

    # ---------------------------------------------------------------- common
    def _render(self, glid, role, secs, order, titles, now, llm, persist, sources=None) -> dict:
        src = sources if sources is not None else self._source_counts(glid, now)
        prev = self.store.doc(glid) if persist else None
        ver = (prev["version"] + 1) if prev else 1
        fm = frontmatter(glid, role, now, ver, src, llm)
        md, tokens, dropped = assemble(secs, order, titles, self.budget, fm, now)
        if persist:
            if prev and prev["md"].split("---", 2)[-1] == md.split("---", 2)[-1]:
                md, ver = prev["md"], prev["version"]  # nothing changed but timestamps
            else:
                ver = self.store.put_doc(glid, role, md, tokens, llm)
                if self.write_files:
                    d = self.out_dir / f"{role}_md"
                    d.mkdir(parents=True, exist_ok=True)
                    (d / f"{glid}.md").write_text(md, encoding="utf-8")
        return {"glid": glid, "role": role, "md": md, "tokens": tokens, "version": ver, "dropped": dropped,
                "llm_enriched": llm}

    def build(self, glid: int, **kw) -> dict:
        role = self.role(glid)
        if role is None:
            raise KeyError(f"GLID {glid} not found")
        if role == "buyer":
            kw.pop("only", None)
            kw.pop("strict_pit", None)
            return self.build_buyer(glid, **kw)
        return self.build_seller(glid, **kw)

    COLD_OPENING = ("Namaste ji, main IndiaMART se Ananya bol rahi hoon. Aap IndiaMART par kuch kharidna chahte hain "
                    "ya apna business badhana chahte hain? Bataiye, main kaise madad kar sakti hoon?")

    def cold_doc(self, glid: int) -> dict:
        """No history anywhere: a clean, generic file so the bot never invents context (cold start)."""
        now = self.now()
        md = (f"---\nglid: {glid}\nrole: unknown\nas_of: {now:%Y-%m-%d %H:%M}\nversion: 0\ncold_start: true\n"
              f"sources: none\n---\n\n# New contact · no IndiaMART history yet\n\n## Before you speak\n"
              f"- No activity on any channel → don't assume buyer or seller; ask one open question.\n"
              f"- Don't claim to know anything about them.\n\n## Suggested opening (Hinglish)\n> {self.COLD_OPENING}\n")
        return {"glid": glid, "role": "unknown", "md": md, "tokens": len(md) // 4, "version": 0, "llm_enriched": False,
                "cold_start": True}

    def ensure(self, glid: int, role: str = "seller") -> str:
        """First activity from an unknown GLID creates an empty profile (cold start → warm on first event)."""
        r = self.role(glid)
        if r is None:
            self.store.put_profiles([(glid, role, {"new_user": True})])
            r = role
        return r

    def get(self, glid: int, max_age_sec: float | None = None) -> dict:
        if self.role(glid) is None:
            return self.cold_doc(glid)
        d = self.store.doc(glid)
        if d is None:
            return self.build(glid)
        return {"glid": glid, "role": d["role"], "md": d["md"], "tokens": d["tokens"], "version": d["version"],
                "llm_enriched": bool(d["llm_enriched"])}

    # ---------------------------------------------------------- live events
    def on_event(self, glid: int, channel: str, kind: str | None, text: str | None,
                 meta: dict | None = None, enrich: bool = True, at: datetime | None = None) -> dict:
        """Ingest one new activity and refresh only the affected sections.

        ``at`` lets a replay feed historical events with their original timestamp.
        """
        received = time.time()
        role = self.ensure(glid)
        now = at or self.now()
        eid = self.store.add_event(glid, now, channel, kind or "", text or "", meta or {}, live=0 if at else 1)
        if role == "seller":
            affected = {s for s, deps in S.SECTION_DEPS.items() if channel in deps} or set(ALL_SELLER)
            # lazy sweep: time-windowed sections (14d / 30d / 7d) drift as time passes, so if this seller's
            # file has not been fully refreshed within FULL_EVERY, refresh everything on this event
            full_at = self.store.sections(glid).get("_full_at")
            if not full_at or (now - datetime.fromisoformat(json.loads(full_at))) > self.FULL_EVERY:
                affected = None
            doc = self.build_seller(glid, only=affected, now=now)
        else:
            doc = self.build_buyer(glid, now=now)
        done = time.time()
        self.store.log_fresh(eid, glid, channel, received, doc_at=done, sections=doc["changed"])
        doc.update(event_id=eid, freshness_ms=round((done - received) * 1000, 1))
        self._notify(glid, {"type": "doc", **doc})
        # AI polish is optional — keep sarvam-105b quota (40/min on Starter) for live conversation turns
        if enrich and self.llm.mode()["llm"] != "offline" and getattr(self.llm, "budget", lambda k: 99)("llm") >= 12:
            self.enqueue_enrich(glid, eid)
        return doc

    # ------------------------------------------------------- LLM enrichment
    ENRICH_SYS = (
        "You maintain a short context file that a Hindi/Hinglish B2B voice agent (Ananya from IndiaMART) reads "
        "before calling a {role}. Using ONLY the facts given, return JSON with keys: "
        "\"open_threads\": list of at most 3 short bullet strings (English, each <= 18 words, newest first, "
        "only things still needing follow-up, each starting with the channel and when), and "
        "\"opening\": one natural Hinglish opening line in Roman script (<= 40 words) that greets, introduces Ananya "
        "from IndiaMART and references the single most relevant recent thing so the user does not have to repeat "
        "themselves. Never invent facts, prices, phone numbers or names."
    )

    def _counterpart_names(self, glid: int, now: datetime) -> set[str]:
        """Other parties' personal names (from enquiry subjects), minus words of this user's own company name."""
        evs = self.store.events(glid, now, channels=["enquiry", "enquiry_reply"])
        names = counterpart_names(e["meta"].get("subject") for e in evs)
        prof = (self.store.profile(glid) or (None, {}))[1] or {}
        own = " ".join(str(v) for v in (prof.get("company_name"), (prof.get("kycdetails") or {}).get("company_name"),
                                        (prof.get("kycdetails") or {}).get("customer_name")) if v).lower()
        return {n for n in names if n not in own}

    def _raw_snippets(self, glid: int, now: datetime, names: set[str] | None = None) -> str:
        evs = self.store.events(glid, now, since=now - timedelta(days=21),
                                channels=[*S.CHAT_CHANNELS, "bot_call", "voice_call", "enquiry_reply", "exec_call"])
        out = []
        for e in evs[:12]:
            # privacy: the LLM must never see (and so never repeat) another party's personal name
            t = clean(scrub_people(clean(e.get("text")), names), 220)
            if e["channel"] == "wa_chat" and e["kind"] not in ("typed", "", None) and not e["meta"].get("live"):
                continue
            if t or e["channel"] == "exec_call":
                out.append(f"[{ago(e['ts'], now)} | {e['channel']} | {e['kind']}] {t}")
        return "\n".join(out[:8])

    def enrich(self, glid: int) -> dict | None:
        doc = self.store.doc(glid)
        if not doc:
            return None
        now = self.now()
        role = doc["role"]
        names = self._counterpart_names(glid, now)
        user = (f"CONTEXT FILE:\n{doc['md']}\n\nRAW RECENT MESSAGES (newest first):\n"
                f"{self._raw_snippets(glid, now, names)}")
        out = self.llm.chat_json([{"role": "system", "content": self.ENRICH_SYS.format(role=role)},
                                  {"role": "user", "content": user}], max_tokens=450)
        if not out or not out.get("opening"):
            return None
        # second guard: scrub the model's output too, in case it inferred a name anyway
        threads = [clean(scrub_people(clean(x), names), 160) for x in (out.get("open_threads") or []) if clean(x)][:3]
        opening = clean(scrub_people(clean(out["opening"]), names), 320)
        self.store.put_section(glid, "opening_llm", json.dumps([opening], ensure_ascii=False))
        if role == "seller":
            self.store.put_section(glid, "threads_llm", json.dumps(threads, ensure_ascii=False))
            d = self.build_seller(glid, only=set())
        else:
            live = self.store.events(glid, now, channels=[*S.CHAT_CHANNELS, "voice_call"])
            self.store.put_section(glid, "_llm_watermark", json.dumps([len(live)]))
            d = self.build_buyer(glid)
        self._notify(glid, {"type": "doc", **d})
        return d

    def enqueue_enrich(self, glid: int, event_id: int | None = None) -> None:
        if glid in self._pending:
            return
        self._pending.add(glid)
        self._q.put((glid, event_id))
        if self._worker is None or not self._worker.is_alive():
            self._worker = threading.Thread(target=self._run_worker, daemon=True)
            self._worker.start()

    def _run_worker(self) -> None:
        while True:
            glid, eid = self._q.get()
            self._pending.discard(glid)
            try:
                d = self.enrich(glid)
                if d and eid:
                    self.store.log_fresh(eid, glid, "", 0, llm_at=time.time())
            except Exception as e:  # never let enrichment kill the worker
                log.exception("enrich failed for %s: %s", glid, e)

    def _notify(self, glid: int, payload: dict) -> None:
        for fn in list(self.listeners):
            try:
                fn(glid, payload)
            except Exception:
                pass

    # ----------------------------------------------------------- bulk build
    def build_all(self, role: str | None = None, limit: int | None = None, log_fn=print) -> dict:
        glids = self.store.glids(role)[: limit or None]
        t0 = time.perf_counter()
        toks = []
        for i, g in enumerate(glids, 1):
            toks.append(self.build(g)["tokens"])
            if i % 500 == 0:
                log_fn(f"  built {i:,}/{len(glids):,}")
        ms = (time.perf_counter() - t0) * 1000
        return {"files": len(glids), "total_ms": round(ms), "ms_per_file": round(ms / max(1, len(glids)), 2),
                "avg_tokens": round(sum(toks) / max(1, len(toks)), 1), "max_tokens": max(toks or [0])}
