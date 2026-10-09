"""Resumption benchmark: does the bot continue across channels without re-asking?

For each scenario a user tells IndiaMART something on WhatsApp (channel 1). Then a voice call starts
(channel 2): we record the bot's opening and its reply to a neutral first user turn ("Haan ji, boliye"),
once with memory ON (the refreshed seller.md) and once with memory OFF (today's cold start).

Metrics, per arm
* resumed      — the bot's first two turns refer to what the user said on WhatsApp
* re_asked     — the bot asks for a fact the user already gave (product, quantity, city, time, question)
* facts repeated per call — how many given facts the user would have to say again

Detection is rule-based (transparent, offline). With a Sarvam key the bot turns come from Sarvam-105B and an
LLM judge double-checks every re-ask verdict.
"""
from __future__ import annotations

import json
import random
from collections import Counter
import re
from pathlib import Path

from .agent import Agent
from .engine import ContextEngine
from .sarvam import client as sarvam_client

SCENARIOS = [
    {"msg": "Mujhe 200 kg {product} chahiye {city} delivery, rate kya hai?",
     "facts": {"product": "{product}", "quantity": "200 kg", "city": "{city}", "question": "rate"}},
    {"msg": "Premium plan ka charges kitna hai? Buy leads kitni milengi?",
     "facts": {"question": "plan charges"}},
    {"msg": "Kal shaam 5 baje ke baad call karna, abhi busy hoon",
     "facts": {"time": "kal shaam 5 baje"}},
    {"msg": "Mujhe {city} ke buyers chahiye, enquiries kam aa rahi hain",
     "facts": {"city": "{city}", "question": "more enquiries"}},
    {"msg": "Mera catalog update karna hai, {product} add karna hai",
     "facts": {"product": "{product}", "question": "catalog update"}},
]
CITIES = ["Jaipur", "Pune", "Surat", "Indore", "Lucknow", "Kolkata"]
ASK = {  # questions that ask the user for a slot
    "product": re.compile(r"(kaun(sa|si)|kis) (product|cheez|item|maal)|kya (product|bechte|chahiye)|which product", re.I),
    "quantity": re.compile(r"kitn(a|i|e) (quantity|maal|kg|piece|unit)|quantity kya|kitna chahiye|how much", re.I),
    "city": re.compile(r"(kis|kaun(se|si)) (city|shehar|location|area)|kahan (se|par|chahiye|deliver)|location kya", re.I),
    "time": re.compile(r"(kis|kaun(sa|se)) (time|samay|din)|kab (call|baat|free|milenge)|kitne baje|time bata", re.I),
    "question": re.compile(r"(kya|kaise) (madad|help) (kar|chahiye)|kis (baare|cheez) (mein|ke)|aapka (sawaal|query) kya", re.I),
}
JUDGE = """You check a phone bot. On WhatsApp the user just wrote: "{msg}"
Facts the user ALREADY gave there (name: value): {facts}.
Here are the bot's first turns on the follow-up call:
{turns}
Return JSON {{"re_asked": [...], "resumed": true|false}} where
- "re_asked" lists ONLY names from the facts above that the bot asks the user to state again (e.g. "kaunsa product?",
  "kis city mein?", "aapka sawaal kya hai?"). Repeating a fact back to confirm it, or proposing / asking for a NEW
  meeting or callback slot, is NOT a re-ask. Use [] if nothing was re-asked.
- "resumed" is true only if the bot refers to THIS latest WhatsApp message (not an older one)."""


def _fill(s: str, product: str, city: str) -> str:
    return s.replace("{product}", product).replace("{city}", city)


def _rule_check(turns: str, facts: dict) -> tuple[list[str], bool]:
    asked = [k for k in facts if ASK.get(k) and ASK[k].search(turns)]
    low = turns.lower()
    distinct = [str(v).lower() for k, v in facts.items() if k in ("product", "quantity", "city", "time") and v]
    keys = [str(v).lower() for v in facts.values() if v]
    # resumed = mentions the given facts, not just the word "WhatsApp" (which an older thread would also produce)
    ref = any(v in low for v in distinct) or ("whatsapp" in low and any(w in low for k in keys for w in k.split()[:2]))
    return asked, ref


def run(eng: ContextEngine, n_sellers: int = 12, seed: int = 7, out_dir: Path | None = None) -> dict:
    rng = random.Random(seed)
    agent = Agent(eng)
    llm = sarvam_client()
    llm.batch = True  # wait for quota instead of falling back to the offline policy mid-benchmark
    glids = eng.store.glids("seller")
    rng.shuffle(glids)
    rows = []
    for g in glids[:n_sellers]:
        prof = eng.store.profile(g)[1]
        product = (prof.get("top_category_1") or "steel pipes").split(",")[0]
        city = rng.choice(CITIES)
        for sc in SCENARIOS:
            msg = _fill(sc["msg"], product, city)
            facts = {k: _fill(v, product, city) for k, v in sc["facts"].items()}
            eng.on_event(g, "wa_chat", "typed", msg, {"live": 1, "eval": "resume"}, enrich=False)
            for arm, mem in (("memory_on", True), ("memory_off", False)):
                op = agent.opening(g, mem)["text"]
                r = agent.reply(g, [{"who": "bot", "text": op}], "Haan ji, boliye", use_context=mem)
                rep = r["text"]
                turns = f"BOT: {op}\nUSER: Haan ji, boliye\nBOT: {rep}"
                asked, resumed = _rule_check(turns, facts)
                judge = None
                if llm.mode()["llm"] != "offline":
                    judge = llm.chat_json([{"role": "user", "content": JUDGE.format(
                        msg=msg, facts=json.dumps(facts, ensure_ascii=False), turns=turns)}], max_tokens=150)
                    if judge:  # the judge may only flag facts the user actually gave
                        asked = sorted(set(asked) | {x for x in (judge.get("re_asked") or []) if x in facts})
                        resumed = bool(judge.get("resumed", resumed))
                rows.append({"glid": g, "scenario": msg, "arm": arm, "facts": list(facts), "re_asked": asked,
                             "resumed": resumed, "turns": turns,
                             "engine": f"{r['engine']}+judge" if judge else r["engine"]})
    res = {"scenarios": len(rows) // 2, "sellers": n_sellers}
    for arm in ("memory_on", "memory_off"):
        rs = [r for r in rows if r["arm"] == arm]
        n_facts = sum(len(r["facts"]) for r in rs)
        res[arm] = {"resumed_pct": round(100 * sum(r["resumed"] for r in rs) / len(rs), 1),
                    "calls_with_a_re_ask_pct": round(100 * sum(bool(r["re_asked"]) for r in rs) / len(rs), 1),
                    "facts_re_asked_pct": round(100 * sum(len(r["re_asked"]) for r in rs) / max(1, n_facts), 1)}
    mix = Counter(r["engine"] for r in rows)
    res["engine"] = next(iter(mix)) if len(mix) == 1 else dict(mix)  # never label a mixed run as pure Sarvam
    if out_dir:
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "resume_eval.json").write_text(json.dumps({"summary": res, "examples": rows}, indent=1,
                                                             ensure_ascii=False), encoding="utf-8")
    return res
