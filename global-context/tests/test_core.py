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
    assert len(long_head) == 2 and long_head[0].endswith("samjha denge.")  # never split mid-sentence
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


def test_caller_can_ask_for_a_language():
    # a caller asking in Hindi for Gujarati used to stay in Hindi
    from gcx.agent import requested_lang
    assert requested_lang("Gujarati mein baat karo") == "gu-IN"
    assert requested_lang("Please speak in English") == "en-IN"
    assert requested_lang("বাংলায় কথা বলুন") == "bn-IN"
    assert requested_lang("Marathi mein kyun bol rahi ho?") == "back"  # a complaint, not a request
    assert requested_lang("Mujhe plan ka rate chahiye") is None


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


def test_phone_call_outbound_request_and_webhook_write_back(monkeypatch):
    """Instant Outbound: body matches the documented OutboundRequest, the webhook writes a connected call back once,
    the agent's on_end hook does not double-write it, and unanswered calls leave memory untouched."""
    from fastapi.testclient import TestClient
    import gcx.api as api
    from gcx import samvaad
    api.engine = eng()
    api.agent.eng = api.engine
    for k, v in {"SARVAM_SAMVAAD_API_KEY": "k3y", "GCX_SAMVAAD_CONNECTION_ID": "conn-1",
                 "GCX_SAMVAAD_AGENT_PHONE_NUMBER": "+918000000000", "GCX_PUBLIC_URL": "https://demo.trycloudflare.com/",
                 "GCX_TUNNEL_TOKEN": "t0ken"}.items():
        monkeypatch.setenv(k, v)
    assert samvaad.normalise_phone("098765 43210") == "+919876543210" == samvaad.normalise_phone("+91 98765-43210")
    sent = {}

    class R:
        status_code, text = 200, ""

        @staticmethod
        def json():
            return {"attempt_id": "att-1"}

    def fake_post(url, json, headers, timeout):
        sent.update(url=url, body=json, headers=headers)
        return R()
    monkeypatch.setattr(samvaad.requests, "post", fake_post)
    c = TestClient(api.app)
    g = 146010610
    assert c.post("/api/phone-call", json={"glid": g, "phone": "9876543210"},
                  headers={"cf-connecting-ip": "1.2.3.4"}).status_code == 403  # never dialable from the tunnel
    r = c.post("/api/phone-call", json={"glid": g, "phone": "9876543210"}).json()
    assert r["attempt_id"] == "att-1" and r["webhook"] and r["phone"].endswith("10") and "xxxx" in r["phone"]
    assert sent["url"].endswith("/orgs/01a1110c-209c-7de3-844d-cbd1f15f165a/workspaces/"
                                "01a1110c-20a4-7547-b624-024fbcef0dc5/outbounds")
    assert sent["headers"]["X-API-Key"] == "k3y"
    b = sent["body"]
    assert b["user_config"] == {"user_phone_number": "+919876543210"}
    assert b["app_config"]["app_version"] == samvaad.settings()["app_version"] and b["app_config"]["connection_config"] == {
        "connection_id": "conn-1", "agent_phone_number": "+918000000000"}
    av = b["app_config"]["agent_variables"]
    assert av["glid"] == str(g) and av["context"].startswith("---") and av["opening"]
    assert b["webhook_config"]["url"] == "https://demo.trycloudflare.com/sarvam/outbound-webhook?token=t0ken"
    assert b["webhook_config"]["metadata"]["glid"] == g

    cf = {"cf-connecting-ip": "1.2.3.4"}
    v0 = api.engine.get(g)["version"]
    # the agent's on_end save_call arrives too — the webhook owns this call, so nothing is written twice
    s = c.post("/sarvam/call-ended?token=t0ken", json={"glid": g, "transcript": "user: haan boliye"}, headers=cf).json()
    assert s.get("skipped") and api.engine.get(g)["version"] == v0
    hook = {"attempt_id": "att-1", "status": "connected", "duration": 42.5, "interaction_id": "20261010/abc",
            "channel_info": {"channel_type": "v2v", "channel_provider": "exotel", "agent_phone_number": "+918000000000"},
            "failure_reason": None, "final_agent_variables": {"glid": str(g)},
            "webhook_config": {"url": "x", "metadata": {"glid": g}},
            "interaction_transcript": [{"role": "agent", "en_text": "Namaste, main Payal, IndiaMART se."},
                                       {"role": "user", "en_text": "Haan, kal 4 baje meeting theek hai."}]}
    assert c.post(samvaad.WEBHOOK_PATH, json=hook, headers=cf).status_code == 403          # token required
    w = c.post(samvaad.WEBHOOK_PATH + "?token=t0ken", json=hook, headers=cf).json()
    assert w["summary"]["disposition"] and w["version"] > v0
    ev = api.engine.store.events(g, api.engine.now(), channels=["voice_call"])[0]
    assert ev["meta"]["attempt_id"] == "att-1" and ev["meta"]["duration"] == 42
    assert c.post(samvaad.WEBHOOK_PATH + "?token=t0ken", json=hook, headers=cf).json().get("duplicate")  # retry
    assert api.engine.get(g)["version"] == w["version"]
    assert not samvaad.webhook_owns(api.engine.store, g)  # resolved → on_end hook works normally again

    # unanswered: shown, not remembered (a voice_call event would close the seller's open WhatsApp question)
    sent.clear()
    R.json = staticmethod(lambda: {"attempt_id": "att-2"})
    c.post("/api/phone-call", json={"glid": g, "phone": "9876543210"})
    v1 = api.engine.get(g)["version"]
    n = c.post(samvaad.WEBHOOK_PATH + "?token=t0ken", headers=cf, json={
        "attempt_id": "att-2", "status": "no_answer", "duration": None, "interaction_id": None,
        "channel_info": {}, "webhook_config": {"url": "x", "metadata": {"glid": g}}, "interaction_transcript": None}).json()
    assert n["status"] == "no_answer" and api.engine.get(g)["version"] == v1
    hist = c.get("/api/phone-calls").json()["attempts"]
    assert [a["status"] for a in hist[:2]] == ["no_answer", "connected"]


def test_phone_call_reports_missing_config(monkeypatch):
    from fastapi.testclient import TestClient
    import gcx.api as api
    api.engine = eng()
    api.agent.eng = api.engine
    monkeypatch.setenv("SARVAM_SAMVAAD_API_KEY", "k3y")
    monkeypatch.setenv("GCX_SAMVAAD_CONNECTION_ID", "")
    monkeypatch.setenv("GCX_SAMVAAD_AGENT_PHONE_NUMBER", "")
    r = TestClient(api.app).post("/api/phone-call", json={"glid": 146010610, "phone": "9876543210"})
    assert r.status_code == 503 and "connection_id" in r.json()["detail"], r.text


def test_tts_lexicon_respells_brands_in_the_target_script():
    from gcx.pronounce import for_tts
    hi = for_tts("Main IndiaMART se bol rahi hoon, WhatsApp par.", "hi-IN")
    assert "इंडियामार्ट" in hi and "व्हाट्सएप" in hi and "मैं" in hi
    assert "IndiaMART" not in hi and "WhatsApp" not in hi
    assert "ઇન્ડિયામાર્ટ" in for_tts("IndiaMART", "gu-IN")
    assert "ইন্ডিয়া মার্ট" in for_tts("IndiaMART", "bn-IN")
    assert for_tts("IndiaMART", "en-IN") == "India Mart"   # all-caps MART invites letter-by-letter spelling
    assert for_tts("IndiaMART", "ta-IN") == "IndiaMART"    # language with no table: left alone


def test_tts_lexicon_transliterates_and_never_translates():
    """/transliterate returns a translation for some words — those are pinned by hand, and a regression
    here would have Payal saying a different word (योजना 'yojana' instead of 'plan')."""
    from gcx.pronounce import LEXICON, for_tts
    assert for_tts("plan", "hi-IN") == "प्लान" and for_tts("plan", "mr-IN") == "प्लान"
    for bad in ("योजना", "खाता", "खाते", "संख्या", "क्रमांक", "भुगतान", "आदेश", "सेवा", "उत्पाद", "मिंट्स"):
        assert bad not in LEXICON["hi-IN"].values() and bad not in LEXICON["mr-IN"].values(), bad


def test_tts_lexicon_matches_whole_latin_words_only():
    from gcx.pronounce import for_tts
    assert for_tts("mainly a domain name", "hi-IN") == "mainly a domain name"  # not "main" inside "mainly"
    assert for_tts("suppliers", "hi-IN") == "सप्लायर्स"                        # longest term wins
    assert for_tts("", "hi-IN") == ""


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok ", name)


def test_samvaad_greeting_is_short_and_memory_point_moves_to_first_turn():
    """Samvaad drops caller audio during the greeting, so only a short hello goes there; the memory point is
    handed to the agent's first (interruptible) turn."""
    from gcx.api import split_greeting
    g, h = split_greeting("Namaste, kya meri baat KPR Tempo se ho rahi hai? Main IndiaMART se Payal bol rahi hoon. "
                          "Pichhli baar aapne baad mein call karne ko kaha tha — kya abhi baat ho sakti hai?", "hi-IN")
    assert g == "Namaste, main IndiaMART se Payal bol rahi hoon — kya meri baat KPR Tempo se ho rahi hai?"
    assert h.startswith("Pichhli baar")
    g, h = split_greeting("Namaste Abhishek ji, main IndiaMART se Payal bol rahi hoon. Aapne PVC Pipe ke liye baat ki thi.", "hi-IN")
    assert g.endswith("kya abhi do minute baat ho sakti hai?") and h.startswith("Aapne PVC")
    assert split_greeting("Main IndiaMART se Payal bol rahi hoon.", "hi-IN") == ("Main IndiaMART se Payal bol rahi hoon.", "")
    g, _ = split_greeting("Namaste, KPR Tempo se baat ho rahi hai? Main IndiaMART se Payal bol rahi hoon. Meeting hui?", "hi-IN")
    assert g == "Namaste, main IndiaMART se Payal bol rahi hoon — KPR Tempo se baat ho rahi hai?"
