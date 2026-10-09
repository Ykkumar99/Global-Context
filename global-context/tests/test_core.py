"""Smoke + correctness tests. Run: python -m pytest -q  (or: python tests/test_core.py)"""
from __future__ import annotations

import os
import sys
import tempfile
from datetime import timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ["GCX_DB_PATH"] = str(Path(tempfile.mkdtemp()) / "test.db")
os.environ["GCX_OUT_DIR"] = str(Path(tempfile.mkdtemp()))
os.environ["SARVAM_API_KEY"] = ""  # tests run offline even when .env holds a real key (setdefault keeps this)

from gcx.config import load_config  # noqa: E402

load_config()
from gcx.engine import ContextEngine  # noqa: E402
from gcx.ingest import ingest_all  # noqa: E402
from gcx.store import Store  # noqa: E402
from gcx.textutil import est_tokens, mask_pii  # noqa: E402

_ENG = None


def eng() -> ContextEngine:
    global _ENG
    if _ENG is None:
        store = Store()
        ingest_all(store, ROOT / "data" / "demo", log=lambda *a: None)
        _ENG = ContextEngine(store)
        _ENG.build_all(log_fn=lambda *a: None)
    return _ENG


def test_every_file_is_valid_and_within_budget():
    e = eng()
    for g in e.store.glids():
        d = e.get(g)
        assert d["md"].startswith("---") and "## Suggested opening" in d["md"]
        assert est_tokens(d["md"]) <= e.budget + 5


def test_live_event_refreshes_only_affected_sections_fast():
    e = eng()
    g = 146010610
    e.build(g)
    d = e.on_event(g, "wa_chat", "typed", "Premium plan ka charges kitna hai?", {"live": 1}, enrich=False)
    assert "Premium plan ka charges kitna hai?" in d["md"]
    assert "pulse" not in d["changed"]
    assert d["freshness_ms"] < 500


def test_call_resolves_open_whatsapp_thread():
    e = eng()
    g = 79859904
    e.on_event(g, "wa_chat", "typed", "Buy leads ki limit kya hai?", {"live": 1}, enrich=False)
    assert "not yet answered" in e.get(g)["md"]
    d = e.on_event(g, "voice_call", "General (talked)", "Explained limits; executive to follow up.",
                   {"live": 1}, enrich=False)
    assert "not yet answered" not in d["md"]


def test_point_in_time_has_no_future_leakage():
    e = eng()
    g = 146010610
    calls = e.store.events(g, e.now(), channels=["bot_call"])
    first = min(c["ts"] for c in calls)
    d = e.build_seller(g, now=first - timedelta(minutes=1), strict_pit=True, persist=False)
    assert "Meeting fixed (" not in d["md"]  # the meeting-fixed call happened later


def test_pii_masked():
    assert "[phone]" in mask_pii("call me at 9815522953")
    assert "[email]" in mask_pii("mail a.b@c.com")


def test_buyer_file_mentions_recent_sellers():
    d = eng().get(73699779)
    assert d["role"] == "buyer" and "Spoke on phone with" in d["md"]


def test_api_end_to_end():
    from fastapi.testclient import TestClient
    import gcx.api as api
    api.engine = eng()
    api.agent.eng = api.engine
    c = TestClient(api.app)
    assert c.get("/api/status").status_code == 200
    assert c.get("/context/146010610.md").text.startswith("---")
    r = c.post("/api/whatsapp", json={"glid": 146010610, "text": "ECS plan ka rate?"}).json()
    assert r["reply"] and r["freshness_ms"] < 500
    s = c.post("/api/call/start", json={"glid": 146010610}).json()
    assert "ECS plan ka rate" in s["text"]
    t = c.post("/api/call/turn", json={"glid": 146010610, "text": "Kal 4 baje theek hai",
                                        "history": [{"who": "bot", "text": s["text"]}]}).json()
    assert t["text"]
    end = c.post("/api/call/end", json={"glid": 146010610, "history": [{"who": "bot", "text": s["text"]},
                                                                       {"who": "user", "text": "Kal 4 baje theek hai"},
                                                                       {"who": "bot", "text": t["text"]}]}).json()
    assert end["summary"]["disposition"]


def test_cold_start_unknown_glid_gets_generic_file():
    e = eng()
    d = e.get(987654321)
    assert d["cold_start"] and "no IndiaMART history" in d["md"]
    d2 = e.on_event(987654321, "wa_chat", "typed", "Kal shaam 5 baje ke baad call karna", {"live": 1}, enrich=False)
    assert "asked to be called" in d2["md"] and "kal shaam 5 baje" in d2["md"].lower()


def test_no_cross_party_names_or_contacts():
    from gcx.evaluate import eval_privacy
    p = eval_privacy(eng())
    assert p["files_quoting_other_party_name"] == 0 and p["files_with_phone_or_email"] == 0


def test_scrub_people():
    from gcx.textutil import counterpart_names, scrub_people
    names = counterpart_names(["Enquiry for Pipes from Shreedhar via IndiaMART"])
    assert scrub_people("Hi Shreedhar, pipes available", names) == "Hi [buyer], pipes available"


def test_files_are_reusable_without_the_bot():
    from gcx.reuse import exec_brief_html, parse_md, segments
    md = eng().get(146010610)["md"]
    d = parse_md(md)
    assert d["meta"]["glid"] == "146010610" and "Suggested opening (Hinglish)" in d["sections"]
    assert "Executive call prep" in exec_brief_html(md)
    assert isinstance(segments([(146010610, md)]), dict)


def test_official_buyer_export_filename_is_detected(tmp_path):
    # the hackathon file is "Global_Context_Problem_Statement_Buyer Side.csv" (space, not underscore)
    import shutil
    from gcx.ingest import load_buyer_contexts
    src = ROOT / "data" / "raw" / "Global_Context_Problem_Statement_Buyer Side.csv"
    if not src.exists():
        import pytest
        pytest.skip("official buyer export not in data/raw")
    shutil.copy(src, tmp_path / src.name)
    items = load_buyer_contexts(tmp_path)
    assert len(items) == 237 and all(it.get("ts", "").startswith("2026-") for it in items)


def test_buyer_file_decodes_keywords_and_uses_newest_touch():
    from gcx.buyer_sections import build_buyer_md_parts
    data = {"kycdetails": {"customer_name": "Test Buyer", "customer_type": "--"},
            "activitydetails": {
                "upload_metadata": {"upload_time": "2026-10-02T10:00:00"},
                "BUYER_ACTIVITY": [
                    {"ACTIVITY_TIME": "20260918134842", "ACTIVITY_TYPE": "Search", "KEYWORD": "sticky%20mats",
                     "CATEGORY_NAME": "-"},
                    {"ACTIVITY_TIME": "20260918134926", "ACTIVITY_TYPE": "ENQ", "KEYWORD": "Clean Room Sticky Mat",
                     "CATEGORY_NAME": "Sticky Mats"}],
                "LAST_LEAD": {"TITLE": "silver%20pouch", "DATE_R": "2026-10-01 00:00:00"},
                "LAST_ENQUIRY": {"TITLE": ""}}}
    sec, opening, _ = build_buyer_md_parts(1, data)
    text = "\n".join(sum(sec.values(), [])) + opening
    assert "%20" not in text and "silver pouch" in opening
    assert sum(1 for l in sec["wants"] if l.lower().startswith("sticky mats")) == 1  # search merged with category
    assert "Account: –" not in text and "Last enquiry" not in text
    assert "2026-10-01" in sec["signals"][0]  # last active = the requirement posted on 1 Oct, not the 18 Sep search


def test_seller_pulse_merges_case_variants():
    from collections import Counter
    from gcx.seller_sections import _top
    assert _top(Counter({"maid service": 3, "Maid Service": 2, "Cook": 4}), 2) == ["maid service", "Cook"]


def test_no_empty_quotes_or_placeholders_in_any_file():
    e = eng()
    for g in e.store.glids():
        md = e.get(g)["md"]
        assert "“”" not in md and "%20" not in md and "⟦" not in md and "Account: –" not in md, g


def test_app_and_web_chat_resume_like_whatsapp():
    # deck: "resumes across voice, WhatsApp, chat and app"
    e = eng()
    g = 79859904
    d = e.on_event(g, "app_chat", "typed", "Catalogue mein naye products kaise add karein?", {"live": 1}, enrich=False)
    assert "App chat" in d["md"] and "naye products kaise add" in d["md"]
    from gcx.agent import Agent
    op = Agent(e).opening(g, True)["text"]
    assert "app par" in op and "naye products" in op
    d = e.on_event(g, "web_chat", "typed", "Kal subah 11 baje call karna", {"live": 1}, enrich=False)
    assert "Web chat" in d["md"] and "11 baje" in d["md"]


def test_parallel_tts_chunks_and_wav_join():
    import io
    import wave
    from gcx.sarvam import Sarvam, _join_wav
    chunks = Sarvam.speech_chunks("Thank you. Main dekh rahi hoon ki aapne WhatsApp par Premium plan ke charges ke baare "
                                  "mein poocha tha, kya aap abhi bhi interested hain?")
    assert chunks[0] == "Thank you." and len(chunks) == 2 and all(c.strip() for c in chunks)
    long_head = Sarvam.speech_chunks("Ji, main exact charges toh nahi bata paungi, par aapke sales executive aapko poora "
                                     "plan detail mein samjha denge. Kal kab free hain?")
    assert long_head[0] == "Ji, main exact charges toh nahi bata paungi," and len(long_head) == 2
    assert Sarvam.speech_chunks("Ji bilkul, kal 4 baje.") == ["Ji bilkul, kal 4 baje."]  # short → one request

    def tone(n):
        b = io.BytesIO()
        with wave.open(b, "wb") as w:
            w.setnchannels(1), w.setsampwidth(2), w.setframerate(22050), w.writeframes(b"\x01\x00" * n)
        return b.getvalue()
    with wave.open(io.BytesIO(_join_wav([tone(100), tone(250)]))) as w:
        assert w.getnframes() == 350 and w.getframerate() == 22050


def test_ai_polish_never_leaks_counterpart_names():
    # found live: the LLM polish saw raw "Hi Panini, ..." replies and wrote the buyer's name into Open threads
    e = eng()
    g = 146010610
    names = e._counterpart_names(g, e.now())
    assert "panini" in names and "kpr" not in names  # the seller's own company word is not a "counterpart"
    assert "Panini" not in e._raw_snippets(g, e.now(), names)

    class LeakyLLM:
        def mode(self):
            return {"llm": "sarvam"}

        def chat_json(self, *a, **k):
            return {"open_threads": ["28 Sep: Replied to buyer Panini asking for catalogue link"],
                    "opening": "Namaste KPR Tempo ji, Panini ko aapne catalogue bheja?"}
    real, e.llm = e.llm, LeakyLLM()
    try:
        md = e.enrich(g)["md"]
    finally:
        e.llm = real
    assert "Panini" not in md and "KPR Tempo" in md


def test_reply_language_follows_the_user():
    # utterances from a real test call: English turns were answered in Hinglish before the fix
    from gcx.agent import detect_lang
    assert detect_lang("Sorry I got confused. Can you please book the meeting for 4:30 PM tomorrow?", "en-IN") == "en-IN"
    assert detect_lang("Yes, you can confirm your executive about this.") == "en-IN"
    assert detect_lang("No no, it's fine from our side.") == "en-IN"
    assert detect_lang("Kal 4 baje theek hai") == "hi-IN"
    assert detect_lang("Haan boliye, kitna charge lagega?") == "hi-IN"
    assert detect_lang("जी नहीं वो meeting तो नहीं हो पाई।") == "hi-IN"
    assert detect_lang("હા, કાલે સાંજે ચાર વાગ્યે ફોન કરજો") == "gu-IN"
    assert detect_lang("माझं नाव राहुल आहे आणि मला", "mr-IN") == "mr-IN"
    # from a real call: Saaras heard Hindi "nahi, thank you" as Marathi "नाही" (mr-IN) and the call flipped to Marathi
    assert detect_lang("नाही thank you", "mr-IN", current="hi-IN") == "hi-IN"
    assert detect_lang("मराठी बघितलं तुला?", "mr-IN", current="hi-IN") == "hi-IN"
    assert detect_lang("ok thank you", "en-IN", current="hi-IN") == "hi-IN"  # too short to switch


def test_rate_limiter_stays_under_plan_limit():
    from gcx.sarvam import _RateLimiter
    rl = _RateLimiter(3)
    assert [rl.acquire(wait=0) for _ in range(4)] == [True, True, True, False] and rl.free() == 0
    rl2 = _RateLimiter(5)
    rl2.saturate()
    assert rl2.free() == 0 and not rl2.acquire(wait=0)


def test_public_tunnel_only_reaches_sarvam_hooks_with_token():
    from fastapi.testclient import TestClient
    import gcx.api as api
    api.engine = eng()
    api.agent.eng = api.engine
    os.environ["GCX_TUNNEL_TOKEN"] = "t0ken"
    c = TestClient(api.app)
    cf = {"cf-connecting-ip": "1.2.3.4"}
    assert c.get("/context/146010610.md", headers=cf).status_code == 403          # demo data not browsable
    assert c.post("/api/call/start", json={"glid": 146010610}, headers=cf).status_code == 403  # no credit burn
    assert c.get("/sarvam/context?glid=146010610", headers=cf).status_code == 403  # no token
    assert c.get("/sarvam/context?glid=146010610&token=wrong", headers=cf).status_code == 403
    assert c.get("/sarvam/context?glid=146010610&token=t0ken", headers=cf).status_code == 200
    assert c.get("/context/146010610.md").status_code == 200                       # local use unaffected
    # an empty Sarvam transcript (unanswered call / tool test) must not write a blank call into memory
    v = api.engine.get(146010610)["version"]
    r = c.post("/sarvam/call-ended?token=t0ken", json={"glid": "146010610", "summary": "", "transcript": ""},
               headers=cf).json()
    assert r.get("skipped") and api.engine.get(146010610)["version"] == v


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok ", name)
