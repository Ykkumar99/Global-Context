"""Conversation layer for the demo: VANI voice agent + WhatsApp bot, both reading
the same context file, both writing back to it.

The *context-aware* agent loads ``seller.md`` / ``buyer.md`` into its system prompt.
The *cold* agent (today's VANI) gets only the company name, for A/B comparison.
With no LLM key, a deterministic dialogue policy keeps the demo fully working.
"""
from __future__ import annotations

import re

from .engine import ContextEngine
from .sarvam import client as sarvam_client
from .textutil import clean

COLD_OPENING = ("Hello, kya meri baat {name} se ho rahi hai? Main IndiaMART se Ananya bol rahi hoon. Main dekh rahi hoon "
                "ki aap IndiaMART ki paid services explore kar rahe the. Is baare mein hamare sales executive aapke saath "
                "ek chhoti si meeting karna chahte hain — kal aap kis time 15–20 minute nikal sakte hain?")

VOICE_SYS = """You are Ananya, an experienced, warm female voice agent from IndiaMART calling a {role} on the phone.
You are a woman: always use feminine verb forms, in every language ("bol rahi hoon" not "bol raha hoon", Gujarati
"bolu chhu / kari rahi chhu").
{lang_rule} 1–2 short sentences per turn, no lists, no emojis, no markdown — your words are converted to speech.
Sound like a real person on a phone call, not a script: relaxed and friendly, small natural acknowledgements
("ji", "achha", "samajh gayi", "bilkul" / in English "sure", "got it", "I understand"), vary your wording, never
repeat a sentence you already said, no formal or bookish words. If you were interrupted, do not restart your
previous sentence — respond to what the caller just said.
{mood_rule}
Goal for sellers: understand their need and, only if it fits, fix a short meeting with a sales executive (ask day/time).
Goal for buyers: understand the requirement and offer to connect verified suppliers.
Rules:
- Use the CONTEXT below. Never ask for anything the context already answers (company, city, products, what they asked
  on WhatsApp, earlier calls). Refer to it naturally ("aapne WhatsApp par poochha tha..."), and keep timings exactly as
  the context gives them ("just now" = "abhi thodi der pehle", "1d ago" = "kal") — never guess a day.
- If the context says they already met/spoke to an executive, do not push a new meeting; ask how it went.
- If they asked not to be called, apologise, confirm opt-out and end.
- If busy, offer a callback time and end. If not interested, thank them and end. Never argue.
- Never invent prices, plan names, numbers or promises. For pricing say the executive will share exact plans.
- Never promise when the executive will call from old notes in the context; ask the caller which day and time suits
  them now.
- Never invent a fact you don't actually know (exact figures, years, personal beliefs/opinions) — say honestly that
  you don't know or don't have an opinion on that, in one short line, then move on.
- If the caller goes off-topic, teases, tests you, or asks something personal (your opinion, astrology, "guess what
  I need", "tell me about yourself"): answer briefly and honestly or with a light line, in the same turn steer back
  to their business need — never abandon the goal to chase the tangent, and never refuse to engage either.
- If the caller accuses you, baits you ("are you calling me stupid", "did that offend you", "you don't even know
  your own company"), or is rude: stay calm, acknowledge once in one short line, do not argue or over-apologise
  (never apologise twice for the same thing), and move the conversation forward.
- If the caller voices distrust (calls IndiaMART a fraud, cites bad reviews): acknowledge the concern once with
  empathy, do not debate facts or get defensive, and invite them to judge for themselves on the short executive
  call instead of over-explaining.
- If the caller keeps deflecting instead of answering a question (teasing, stalling, repeating the same test):
  after one light redirect, stop re-asking — propose a concrete day/time yourself and move the call toward closing.
- If the caller says they did not hear you ("kya bola?", "sunai nahi diya"), repeat your last point in fewer words —
  never ask "ab sunai de raha hai?" and never comment on the line.
- Privacy: never reveal another buyer's or seller's name, phone number, messages or quoted prices. Refer to them
  only generically ("ek buyer ne Mumbai se enquiry bheji hai").
- If the CONTEXT says cold_start / no history, do not pretend to know them: introduce yourself and ask one open question.
- If they ask whether you are a bot, say honestly you are IndiaMART's AI assistant.
- Stay on the topic you just raised: if your last turn asked about something (e.g. their WhatsApp question) and they
  say "haan / boliye / ok", continue that same topic — do not jump to a different thread from the context.
- When you confirm a day or time the user just gave, repeat their exact words ("kal shaam 4 baje" stays "kal", never
  "aaj"); if it is unclear, ask once instead of guessing.
- The newest message (the one your opening referred to) is what matters now. Do not bring up OLDER messages or
  requirements from "Last conversations" unless the user mentions them — they may already be resolved.
CONTEXT ({mode}):
{context}"""

WA_SYS = """You are IndiaMART's chat assistant (WhatsApp, app or web chat) replying to a {role}. Reply in the user's language style
(Hinglish/English), max 2 short sentences, friendly, no markdown headings. Use the CONTEXT so the user never has to
repeat anything they told IndiaMART on another channel (calls, WhatsApp, enquiries). If they ask for pricing or plans,
say an executive will share exact details and offer a call. Never invent numbers. Never reveal another party's name,
number or messages.
This is a TEXT chat, not a phone call: reply directly to their latest message. Never say you are calling, never ask
"do minute milenge", and do not reuse the "Suggested opening" from the context — that line is only for voice calls.
CONTEXT:
{context}"""

SUMMARY_SYS = """Summarise this IndiaMART call for the user's context file. Return JSON:
{"disposition": one of ["Meeting Fixed","Call Later / Busy","Not Interested","General (talked)"],
 "summary": "<= 30 words, English, what the user said/wants and what was agreed (include day/time if any)",
 "follow_up": "<= 12 words or empty"}"""

YES = re.compile(r"\b(haan|haa|ha|ji|yes|ok|okay|theek|thik|sure|bilkul|chalega|kar (?:do|dijiye))\b", re.I)
NO = re.compile(r"\b(nahi|nahin|no|not interested|mat|zarurat nahi|need nahi)\b", re.I)
BUSY = re.compile(r"\b(busy|baad mein|later|abhi nahi|meeting mein|drive|bahar|kal call|call back)\b", re.I)
PRICE = re.compile(r"\b(price|charges?|kitna|kitne|plan|package|cost|fees?|paisa|rate)\b", re.I)
MET = re.compile(r"\b(mil (?:chuke|liya|gaye)|already|pehle se|executive se baat|meeting ho gayi)\b", re.I)
BOT = re.compile(r"\b(bot|robot|ai|a\.i\.|recorded)\b", re.I)
TIME = re.compile(r"\b(\d{1,2}\s*(?:baje|am|pm|bje)|subah|shaam|dopahar|kal|parso|monday|tuesday|wednesday|thursday|"
                  r"friday|saturday|sunday|somvar|mangal|budh|guru|shukr|shani)\b", re.I)


LANG_CODES = {"hindi": "hi-IN", "english": "en-IN", "gujarati": "gu-IN", "marathi": "mr-IN", "tamil": "ta-IN",
              "telugu": "te-IN", "kannada": "kn-IN", "malayalam": "ml-IN", "bengali": "bn-IN", "punjabi": "pa-IN",
              "odia": "od-IN", "oriya": "od-IN"}
LANG_NAMES = {v: k.title() for k, v in LANG_CODES.items()}

# Unicode blocks of Indic scripts -> language code (Devanagari defaults to Hindi unless the hint says Marathi)
_SCRIPTS = [("hi-IN", 0x0900, 0x097F), ("bn-IN", 0x0980, 0x09FF), ("pa-IN", 0x0A00, 0x0A7F), ("gu-IN", 0x0A80, 0x0AFF),
            ("od-IN", 0x0B00, 0x0B7F), ("ta-IN", 0x0B80, 0x0BFF), ("te-IN", 0x0C00, 0x0C7F), ("kn-IN", 0x0C80, 0x0CFF),
            ("ml-IN", 0x0D00, 0x0D7F)]
_HINGLISH = re.compile(r"\b(hai|hain|haan|haa|nahi|nahin|kya|kaise|kab|kitna|kitne|kitni|aap|aapka|aapko|mujhe|mera|"
                       r"meri|mere|theek|thik|ji|kar|karo|karna|karwa|dijiye|baje|kal|aaj|parso|mein|bhi|toh|acha|"
                       r"achha|boliye|bolo|chahiye|wala|wali|baat|abhi|hoon|raha|rahi|gaya|gayi|sahi|matlab|lekin)\b",
                       re.I)


_MOODS = [  # checked in this order; Hinglish, English and Devanagari cues from real VANI pushback
    ("frustrated", re.compile(
        r"baar baar|roz roz|roz call|kitni baar|pareshan|irritat|gussa|bakwas|faltu|bekar|time waste|waste of time|"
        r"mat karo|band karo|disturb|already (?:told|said)|bola na|bataya na|stop calling|annoying|worst|fraud|"
        r"परेशान|गुस्सा|बार बार|बकवास|फालतू|बेकार|मत करो|बंद करो|!{2,}", re.I)),
    ("busy", re.compile(
        r"\bbusy\b|meeting (?:mein|me)|driving|gaadi chala|baad (?:mein|me)|\blater\b|abhi nahi|call back|"
        r"jaldi (?:bolo|batao)|in a hurry|बिजी|बाद में|अभी नहीं|जल्दी", re.I)),
    ("confused", re.compile(
        r"samajh nahi|samjha nahi|kya matlab|matlab\?|kya bol rahe|kaun bol|phir se bolo|dobara bolo|"
        r"didn'?t (?:understand|get)|confus|what do you mean|repeat|समझ नहीं|क्या मतलब|फिर से", re.I)),
    ("positive", re.compile(
        r"badhiya|bahut achha|great|thank|shukriya|dhanyavaad|perfect|awesome|interested|zaroor|bilkul|"
        r"बढ़िया|धन्यवाद|शुक्रिया|ज़रूर|जरूर|बिल्कुल", re.I)),
]
MOOD_STYLE = {
    "frustrated": "The caller sounds annoyed or frustrated. Open with one short, sincere acknowledgement or apology, "
                  "do not pitch anything, keep it to one sentence, and offer to call later or stop.",
    "busy": "The caller is busy. Acknowledge it, ask for a good callback time in one short sentence, and wrap up.",
    "confused": "The caller is confused. Slow down and explain in one simple sentence, no jargon, then check "
                "if it is clear.",
    "positive": "The caller is warm and positive. Match their energy and move ahead efficiently.",
    "neutral": "",
}
MOOD_PACE = {"frustrated": 0.96, "confused": 0.95, "busy": 1.1, "positive": 1.07, "neutral": 1.03}


def detect_mood(text: str) -> str:
    """Caller mood from their words — steers tone, length and speaking pace of the next reply."""
    for mood, pat in _MOODS:
        if pat.search(text or ""):
            return mood
    return "neutral"


_MR_WORDS = set("आहे आहेत नाही नको काय कसं कसे मला मी तुम्ही तुमचा तुमची तुमचं तुला माझं माझा माझी आणि होय झालं "
                "झाला बघितलं सांगा करतो करते करायचं आम्ही वाजता वाजताची संध्याकाळी उद्या आहात".split())
_HI_WORDS = set("है हैं नहीं क्या मुझे मेरा मेरी आप आपका आपको और लेकिन हाँ हां कल बजे करो ठीक चाहिए था थी रहा रही "
                "हूँ हूं बोलिए बताइए दो दीजिए".split())


_LANG_ASKED = [  # how callers name a language, in Roman, Devanagari and the language's own script
    ("gu-IN", r"gujarati|gujrati|गुजराती|ગુજરાતી"), ("mr-IN", r"marathi|मराठी"), ("ta-IN", r"tamil|तमिल|தமிழ்"),
    ("te-IN", r"telugu|तेलुगु|తెలుగు"), ("bn-IN", r"bengali|bangla|बंगाली|बांग्ला|বাংলা"),
    ("kn-IN", r"kannada|कन्नड़|कन्नड|ಕನ್ನಡ"), ("ml-IN", r"malayalam|मलयालम|മലയാളം"),
    ("pa-IN", r"punjabi|पंजाबी|ਪੰਜਾਬੀ"), ("od-IN", r"odia|oriya|ओड़िया|ओडिया|ଓଡ଼ିଆ"),
    ("en-IN", r"english|इंग्लिश|अंग्रेज़ी|अंग्रेजी"), ("hi-IN", r"hindi|हिंदी|हिन्दी"),
]
_ASK_VERB = re.compile(r"\b(baat|bolo|boliye|bolna|bol|karo|kijiye|kar|samjhao|batao|speak|talk|reply|switch|continue|"
                       r"bolun|kotha|pesu|pesungal|matladandi|matladu|maatanadi|vaat|bola)\b"
                       r"|बात|बोलो|बोलिए|बोल|करो|कीजिए|समझाओ|बताओ|বলুন|কথা|பேசுங்கள்|మాట్లాడండి|ಮಾತನಾಡಿ|વાત", re.I)
_COMPLAINT = re.compile(r"\b(kyun|kyon|kyu|why|mat|don'?t|stop)\b|क्यों|क्यूं|मत", re.I)


def requested_lang(text: str) -> str | None:
    """A caller who *asks* for a language ("Gujarati mein baat karo", "speak in Tamil") is switched to it even
    though they asked in Hindi — before this, the reply stayed Hindi. "Marathi mein kyun bol rahi ho?" is a
    complaint, not a request -> "back" (reset to the language they are actually speaking)."""
    for code, names in _LANG_ASKED:
        if re.search(names, text or "", re.I):
            if _COMPLAINT.search(text):
                return "back"
            if _ASK_VERB.search(text):
                return code
    return None


def detect_lang(text: str, hint: str | None = None, current: str | None = None) -> str:
    """Language of what the caller just said, kept stable across a call.

    ``hint`` is the speech-to-text guess, ``current`` the language the call is in. Indic scripts other than
    Devanagari are unambiguous. Devanagari Hindi vs Marathi is not: Saaras once turned a Hindi "nahi, thank you"
    into Marathi "नाही" (mr-IN) and the whole call flipped to Marathi — so we switch only on clear evidence
    (STT says mr-IN, 4+ words, 2+ Marathi-only words, no Hindi words). Very short replies never change language."""
    current = current or "hi-IN"
    counts: dict[str, int] = {}
    for ch in text or "":
        o = ord(ch)
        for code, lo, hi in _SCRIPTS:
            if lo <= o <= hi:
                counts[code] = counts.get(code, 0) + 1
    tokens = re.findall(r"[\wऀ-෿']+", text or "")
    if counts:
        code = max(counts, key=counts.get)
        if code != "hi-IN":
            return code
        words = [t.strip("।.,?!") for t in tokens]
        mr = sum(w in _MR_WORDS for w in words)
        hi = sum(w in _HI_WORDS for w in words)
        if current == "mr-IN":  # a Marathi call stays Marathi unless the caller clearly speaks Hindi
            return "hi-IN" if hi >= 2 and mr == 0 else "mr-IN"
        if hint == "mr-IN" and len(words) >= 4 and mr >= 2 and hi == 0:
            return "mr-IN"
        return "hi-IN"
    words = re.findall(r"[A-Za-z']+", text or "")
    if not words:
        return current
    if len(_HINGLISH.findall(text)) / len(words) >= 0.15:
        return "hi-IN"
    if len(words) < 4:  # "ok", "thank you", "yes sure" — too short to be a language switch
        return current
    return "en-IN"


class Agent:
    def __init__(self, engine: ContextEngine):
        self.eng = engine
        self.llm = sarvam_client()

    # ---------------------------------------------------------------- utils
    def _ctx(self, glid: int, use_context: bool) -> tuple[str, str, str]:
        doc = self.eng.get(glid)
        role = doc["role"]
        prof = (self.eng.store.profile(glid) or (None, {}))[1]
        name = clean(prof.get("company_name")) or clean((prof.get("kycdetails") or {}).get("company_name")) or "aap"
        if use_context:
            return role, name, doc["md"]
        return role, name, f"Company: {name}. (No other history available — cold call.)"

    @staticmethod
    def _opening_from_md(md: str) -> str | None:
        m = re.search(r"## Suggested opening.*?\n> (.+)", md)
        return m.group(1).strip() if m else None

    def language(self, glid: int, use_context: bool = True) -> str:
        """Preferred call language from evidence in past calls (falls back to Hinglish)."""
        if not use_context or self.eng.role(glid) != "seller":
            return "hi-IN"
        cnt: dict[str, int] = {}
        for e in self.eng.store.events(glid, self.eng.now(), channels=["pns_extract"]):
            for l in re.findall(r"[A-Za-z]+", str(e["meta"].get("languages", ""))):
                code = LANG_CODES.get(l.lower())
                if code and code != "en-IN":
                    cnt[code] = cnt.get(code, 0) + 1
        if not cnt:
            return "hi-IN"
        best = max(cnt, key=cnt.get)
        return best if cnt[best] >= max(2, cnt.get("hi-IN", 0)) else "hi-IN"

    # -------------------------------------------------------------- voice
    def opening(self, glid: int, use_context: bool = True) -> dict:
        role, name, md = self._ctx(glid, use_context)
        line = (self._opening_from_md(md) if use_context else None) or COLD_OPENING.format(name=name)
        lang = self.language(glid, use_context)
        if lang != "hi-IN":
            out = self.llm.chat([{"role": "system", "content":
                                  f"Translate this phone greeting into natural spoken {LANG_NAMES[lang]} in native script. "
                                  f"The speaker, Ananya, is a woman: use feminine first-person verb forms. "
                                  f"Keep names, 'IndiaMART' and product names as is. Return only the translation."},
                                 {"role": "user", "content": line}], max_tokens=200, temperature=0.2)
            if out:
                return {"text": clean(out, 400, strip_urls=False), "lang": lang, "source_text": line}
            lang = "hi-IN"
        return {"text": line, "lang": lang}

    def reply(self, glid: int, history: list[dict], user_text: str, use_context: bool = True,
              channel: str = "voice", lang: str = "hi-IN", mood: str = "neutral") -> dict:
        role, name, md = self._ctx(glid, use_context)
        # the language rule leads the prompt: Sarvam-105B follows the first instruction over a Hinglish history
        if lang == "en-IN":
            lang_rule = ("The caller is speaking ENGLISH: reply only in simple, natural Indian English (Latin script) "
                         "— no Hindi words like 'kal', 'baje', 'theek hai'. If they switch to Hindi, switch with them.")
        elif lang == "hi-IN":
            lang_rule = ("Speak natural Hinglish in Roman script (Hindi grammar, common English business words). "
                         "If the caller switches to English or another language, reply in that language.")
        else:
            lang_rule = (f"The caller is speaking {LANG_NAMES.get(lang, lang).upper()}: reply only in "
                         f"{LANG_NAMES.get(lang, lang)} (native script). If they switch language, switch with them.")
        fmt = {"role": role, "context": md, "mode": "full history" if use_context else "cold start"}
        mood_rule = f"CALLER MOOD NOW: {mood}. {MOOD_STYLE.get(mood, '')}" if MOOD_STYLE.get(mood) else ""
        sys = (VOICE_SYS.format(lang_rule=lang_rule, mood_rule=mood_rule, **fmt) if channel == "voice"
               else WA_SYS.format(**fmt))
        msgs = [{"role": "system", "content": sys}]
        for h in history[-12:]:
            msgs.append({"role": "assistant" if h["who"] == "bot" else "user", "content": h["text"]})
        # the system prompt alone loses to a Hinglish history, so restate the language on the latest turn
        note = {"en-IN": "\n\n[Reply in English only.]",
                "hi-IN": "\n\n[Reply in Hinglish only - Roman-script Hindi.]"}.get(
            lang, f"\n\n[Reply in {LANG_NAMES.get(lang, lang)} only, native script.]") if channel == "voice" else ""
        msgs.append({"role": "user", "content": user_text + note})
        out = self.llm.chat(msgs, max_tokens=180, temperature=0.4)
        # the model tends to copy the language of earlier turns (a Gujarati stretch, then "ab Hindi mein boliye"
        # still came back in Gujarati); Hinglish and Devanagari Hindi both count as Hindi
        got = detect_lang(out or "", current=lang)
        wrong = (got not in ("hi-IN", "en-IN")) if lang == "hi-IN" else (got != lang)
        if out and channel == "voice" and wrong:
            target = {"en-IN": "simple, natural Indian English (no Hindi words)",
                      "hi-IN": "natural Hinglish in Roman script (Hindi grammar, everyday English words)"}.get(
                lang, f"{LANG_NAMES.get(lang, lang)} in native script")
            fixed = self.llm.chat([{"role": "system", "content": f"Rewrite this phone reply in {target}. Keep the "
                                    "meaning, names, days and times exactly. The speaker is a woman. Return only "
                                    "the rewritten reply."},
                                   {"role": "user", "content": out}], max_tokens=180, temperature=0.2)
            out = fixed or out
        if out:
            return {"text": clean(out.replace("\n", " "), 400, strip_urls=False), "engine": self.llm.mode()["llm"],
                    "end": bool(re.search(r"dhanyavaad|dhanyavad|shubh ho|thank you.*day|alvida", out, re.I))}
        return self._offline_reply(glid, history, user_text, md, use_context, channel)

    def _offline_reply(self, glid, history, text, md, use_context, channel) -> dict:
        """Deterministic policy so the demo runs with no API key."""
        t = text.lower()
        met = use_context and "IndiaMART executive" in md
        asked_q = re.search(r"(?:WhatsApp|App chat|Web chat) [^\n]*: “([^”]+)”", md) if use_context else None
        said_time = re.search(r"asked to be called “([^”]+)”", md) if use_context else None
        end = False
        if BOT.search(t):
            r = "Ji, main IndiaMART ki AI assistant Ananya hoon. Aapki madad ke liye hi call kiya hai."
        elif BUSY.search(t):
            r = "Koi baat nahi ji. Aap bataiye kis time call karoon — main usi time dobara call kar loongi."
            if TIME.search(t):
                when = " ".join(dict.fromkeys(m.group(0) for m in TIME.finditer(t)))
                r = f"Theek hai ji, main {when} call kar loongi. Dhanyavaad, aapka din shubh ho."
                end = True
        elif MET.search(t):
            r = ("Achha, aapki executive se baat ho chuki hai — bahut badhiya. Kya unhone aapki query solve kar di, "
                 "ya kuch aur madad chahiye?")
        elif PRICE.search(t):
            r = ("Ji, exact plan aur charges aapke business ke hisaab se hamare executive hi bata payenge. "
                 "Kya main unke saath 15 minute ki call ya meeting fix kar doon? Aapko kab theek rahega?")
        elif TIME.search(t) and history:
            when = " ".join(dict.fromkeys(m.group(0) for m in TIME.finditer(t)))
            r = (f"Perfect, {when} ke liye meeting fix kar rahi hoon. Executive aapko confirm "
                 f"karenge. Dhanyavaad, aapka din shubh ho.")
            end = True
        elif NO.search(t):
            r = "Koi baat nahi ji, aapka samay dene ke liye dhanyavaad. Aapka din shubh ho."
            end = True
        elif YES.search(t):
            if said_time:
                r = ("Dhanyavaad ji. Aapki IndiaMART profile aur enquiries ke liye hamare executive ek chhoti si call "
                     "karna chahte hain — kya main unki call bhi isi time rakh doon?")
            elif asked_q:
                q = asked_q.group(1)
                r = (f"Ji, aapne message mein “{q[:60]}” poochha tha — iske exact details hamare executive denge. "
                     f"Kya main unke saath 15 minute ki call fix kar doon?")
            elif met:
                r = "Badhiya. Kya executive ke saath baat ke baad koi naya sawaal hai jisme main madad karoon?"
            else:
                r = "Badhiya! Hamare sales executive aapko 15 minute mein poori jaankari denge — kal kis time theek rahega?"
        else:
            r = "Ji, samajh gayi. Kya main isme aapki madad ke liye hamare executive ke saath ek chhoti call fix kar doon?"
        if channel == "whatsapp":
            r = r.replace("call kar loongi", "message/call karenge")
        return {"text": r, "engine": "offline-policy", "end": end}

    # ------------------------------------------------------------ wrap-up
    def summarize(self, history: list[dict]) -> dict:
        convo = "\n".join(f"{'Agent' if h['who'] == 'bot' else 'User'}: {h['text']}" for h in history)
        out = self.llm.chat_json([{"role": "system", "content": SUMMARY_SYS}, {"role": "user", "content": convo}],
                                 max_tokens=200)
        if out and out.get("summary"):
            return {"disposition": out.get("disposition") or "General (talked)", "summary": clean(out["summary"], 220),
                    "follow_up": clean(out.get("follow_up"), 80)}
        users = " ".join(h["text"] for h in history if h["who"] != "bot").lower()
        last_bot = next((h["text"] for h in reversed(history) if h["who"] == "bot"), "")
        if "meeting fix" in last_bot.lower():
            disp = "Meeting Fixed"
        elif BUSY.search(users):
            disp = "Call Later / Busy"
        elif NO.search(users) and not YES.search(users):
            disp = "Not Interested"
        else:
            disp = "General (talked)"
        said = [h["text"] for h in history if h["who"] != "bot"]
        times = list(dict.fromkeys(m.group(0) for m in TIME.finditer(users)))
        summary = (f"User said: “{clean(' / '.join(said[-2:]), 120)}”."
                   + (f" Time agreed: {' '.join(times[-3:])}." if times else ""))
        return {"disposition": disp, "summary": summary, "follow_up": ""}

    def end_call(self, glid: int, history: list[dict], channel_label: str = "VANI demo call",
                 meta: dict | None = None) -> dict:
        s = self.summarize(history)
        doc = self.eng.on_event(glid, "voice_call", s["disposition"], s["summary"],
                                {"agent": channel_label, "turns": len(history), "live": 1,
                                 "duration": sum(len(h["text"]) for h in history) // 12, **(meta or {})})
        return {"summary": s, "doc": doc}
