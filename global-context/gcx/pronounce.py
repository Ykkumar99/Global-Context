"""Pronunciation fixes applied to the text just before it is handed to Bulbul.

A voice speaking an Indic language has to guess at Latin-script words, so brand names arrive mangled
("IndiaMART", "WhatsApp"). Writing them in the target script makes the pronunciation explicit and,
unlike the engine's own guess, identical on every call.

The tables were generated with Sarvam's /transliterate (spoken_form=True) and then audited twice, because
that endpoint sometimes returns a *translation* instead of a transliteration — "plan" came back as योजना
(yojana) and "account" as खाता (khata), which would have Payal saying a different word:

  1. Round-trip: every entry transliterated back to Latin and compared with the source term. That caught
     Bengali "enquiry" -> এনকাউন্টার ("Encounter") and "buyers" -> ওয়ার্স ("Worse").
  2. Hand review of the Devanagari and Gujarati tables, because a round-trip can launder a translation:
     सेवा comes back as "Service" even though it is read "seva".

Bengali, Telugu and Kannada carry only the brand names. Those round-trip exactly in every language; the
rest of those tables could not be reviewed by eye, and a wrong entry is worse than letting Bulbul guess.
"""
from __future__ import annotations

import re

DEVANAGARI_HI = {
    "account": "अकाउंट",
    "app": "ऐप",
    "buyer": "बायर",
    "buyers": "बायर्स",
    "call": "कॉल",
    "catalogue": "कैटलॉग",
    "charges": "चार्जेस",
    "connect": "कनेक्ट",
    "dashboard": "डैशबोर्ड",
    "delivery": "डिलीवरी",
    "email": "ईमेल",
    "enquiries": "एनक्वायरीज़",
    "enquiry": "एनक्वायरी",
    "executive": "एक्ज़ेक्यूटिव",
    "indiamart": "इंडियामार्ट",
    "invoice": "इनवॉइस",
    "lead": "लीड",
    "leads": "लीड्स",
    "listing": "लिस्टिंग",
    "main": "मैं",
    "maine": "मैंने",
    "meeting": "मीटिंग",
    "membership": "मेंबरशिप",
    "minute": "मिनट",
    "minutes": "मिनट्स",
    "mobile": "मोबाइल",
    "number": "नंबर",
    "online": "ऑनलाइन",
    "options": "ऑप्शन्स",
    "order": "ऑर्डर",
    "package": "पैकेज",
    "payment": "पेमेंट",
    "photo": "फोटो",
    "plan": "प्लान",
    "premium": "प्रीमियम",
    "price": "प्राइस",
    "product": "प्रोडक्ट",
    "products": "प्रोडक्ट्स",
    "profile": "प्रोफ़ाइल",
    "quotation": "क्वोटेशन",
    "rate": "रेट",
    "refund": "रिफंड",
    "requirement": "रिक्वायरमेंट",
    "service": "सर्विस",
    "stock": "स्टॉक",
    "subscription": "सब्सक्रिप्शन",
    "supplier": "सप्लायर",
    "suppliers": "सप्लायर्स",
    "verified": "वेरिफाइड",
    "video": "वीडियो",
    "website": "वेबसाइट",
    "whatsapp": "व्हाट्सएप",
}

DEVANAGARI_MR = {
    "account": "अकाउंट",
    "app": "ऐप",
    "buyer": "बॉयर",
    "buyers": "बायर्स",
    "call": "कॉल",
    "catalogue": "कॅटलॉग",
    "charges": "चार्जेस",
    "connect": "कनेक्ट",
    "dashboard": "डॅशबोर्ड",
    "delivery": "डिलिवरी",
    "email": "ईमेल",
    "enquiries": "एन्क्वारीज",
    "enquiry": "एन्क्वायरी",
    "executive": "एक्झिक्युटिव्ह",
    "indiamart": "इंडियामार्ट",
    "invoice": "इनव्हॉइस",
    "lead": "लीड",
    "leads": "लीड्स",
    "listing": "लिस्टिंग",
    "main": "मैं",
    "maine": "मैंने",
    "meeting": "मीटिंग",
    "membership": "मेंबरशिप",
    "minute": "मिनिट",
    "minutes": "मिनिट्स",
    "mobile": "मोबाइल",
    "number": "नंबर",
    "online": "ऑनलाइन",
    "options": "ऑप्शन्स",
    "order": "ऑर्डर",
    "package": "पॅकेज",
    "payment": "पेमेंट",
    "photo": "फोटो",
    "plan": "प्लान",
    "premium": "प्रीमियम",
    "price": "प्राइस",
    "product": "प्रॉडक्ट",
    "products": "प्रॉडक्ट्स",
    "profile": "प्रोफाइल",
    "quotation": "क्वोटेशन",
    "rate": "रेट",
    "refund": "रिफंड",
    "requirement": "रिक्वायरमेंट",
    "service": "सर्विस",
    "stock": "स्टॉक",
    "subscription": "सबस्क्रिप्शन",
    "supplier": "सप्लायर",
    "suppliers": "सप्लायर्स",
    "verified": "व्हेरिफाइड",
    "video": "व्हिडिओ",
    "website": "वेबसाइट",
    "whatsapp": "व्हॉट्सअ‍ॅप",
}

GUJARATI = {
    "account": "એકાઉન્ટ",
    "app": "એપ",
    "buyer": "બાયર",
    "buyers": "બાયર્સ",
    "call": "કોલ",
    "catalogue": "કેટેલોગ",
    "charges": "ચાર્જીસ",
    "connect": "કનેક્ટ",
    "dashboard": "ડેશબોર્ડ",
    "delivery": "ડિલિવરી",
    "email": "ઈમેલ",
    "enquiries": "એન્ક્વાયરીઝ",
    "enquiry": "ઇન્ક્વાયરી",
    "executive": "એક્ઝિક્યુટિવ",
    "indiamart": "ઇન્ડિયામાર્ટ",
    "invoice": "ઇન્વોઇસ",
    "lead": "લીડ",
    "leads": "લીડ્સ",
    "listing": "લિસ્ટિંગ",
    "meeting": "મીટિંગ",
    "membership": "મેમ્બરશીપ",
    "minute": "મિનિટ",
    "minutes": "મિનિટ્સ",
    "mobile": "મોબાઈલ",
    "number": "નંબર",
    "online": "ઓનલાઇન",
    "options": "ઓપ્શન્સ",
    "order": "ઓર્ડર",
    "package": "પેકેજ",
    "payment": "પેમેન્ટ",
    "photo": "ફોટો",
    "plan": "પ્લાન",
    "premium": "પ્રીમિયમ",
    "price": "પ્રાઈસ",
    "product": "પ્રોડક્ટ",
    "products": "પ્રોડક્ટ્સ",
    "profile": "પ્રોફાઈલ",
    "quotation": "ક્વોટેશન",
    "rate": "રેટ",
    "refund": "રિફંડ",
    "requirement": "રિકવાયરમેન્ટ",
    "service": "સર્વિસ",
    "stock": "સ્ટોક",
    "subscription": "સબ્સ્ક્રિપ્શન",
    "supplier": "સપ્લાયર",
    "suppliers": "સપ્લાયર્સ",
    "verified": "વેરિફાઇડ",
    "video": "વિડિયો",
    "website": "વેબસાઈટ",
    "whatsapp": "વોટ્સએપ",
}

BRAND_ONLY = {
    "bn-IN": {"indiamart": "ইন্ডিয়া মার্ট", "whatsapp": "হোয়াট্‌সঅ্যাপ"},
    "te-IN": {"indiamart": "ఇండియామార్ట్", "whatsapp": "వాట్సాప్"},
    "kn-IN": {"indiamart": "ಇಂಡಿಯಾಮಾರ್ಟ್", "whatsapp": "ವಾಟ್ಸಾಪ್"},
}

ENGLISH = {
    "indiamart": "India Mart",
}


LEXICON: dict[str, dict[str, str]] = {
    "hi-IN": DEVANAGARI_HI, "mr-IN": DEVANAGARI_MR, "gu-IN": GUJARATI, "en-IN": ENGLISH, **BRAND_ONLY,
}

# Longest term first so "suppliers" wins over "supplier"; Latin-only guards keep us from matching inside a
# word we have already replaced with native script.
_PATTERNS = {
    lang: re.compile(r"(?<![A-Za-z])(" + "|".join(re.escape(t) for t in sorted(tbl, key=len, reverse=True))
                     + r")(?![A-Za-z])", re.I)
    for lang, tbl in LEXICON.items() if tbl
}


def for_tts(text: str, lang: str) -> str:
    """Respell known terms in ``lang``'s own script so the voice pronounces them the same way every time."""
    pat, tbl = _PATTERNS.get(lang), LEXICON.get(lang)
    if not pat or not text:
        return text
    return pat.sub(lambda m: tbl[m.group(1).lower()], text)
