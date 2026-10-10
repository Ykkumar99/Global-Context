"""Regenerate the gcx/pronounce.py tables.  Run: python scripts/build_pronunciation_lexicon.py [--write]

Asks Sarvam's /transliterate for each term in each language, then audits the answers, because that endpoint
sometimes returns a *translation* rather than a transliteration ("plan" -> योजना, "account" -> खाता) — which
would make the voice say a different word. Two checks:

  * round-trip: transliterate the result back to Latin and compare with the source term. Catches the gross
    failures, including ones in scripts you cannot read (Bengali "enquiry" -> "Encounter").
  * OVERRIDES below: hand-pinned spellings for the cases a round-trip launders — सेवा comes back as
    "Service" even though it is read "seva", so it has to be caught by eye.

Without --write it only prints the audit, which is the useful mode when adding terms: add to TERMS, run,
and read the SUSPECT list before trusting anything.
"""
from __future__ import annotations

import argparse
import difflib
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
API = "https://api.sarvam.ai/transliterate"

TERMS = ["IndiaMART", "WhatsApp", "Premium", "buyer", "buyers", "supplier", "suppliers", "enquiry",
         "enquiries", "requirement", "catalogue", "lead", "leads", "plan", "package", "membership",
         "subscription", "executive", "meeting", "minute", "minutes", "options", "product", "products",
         "verified", "account", "website", "app", "email", "number", "dashboard", "profile", "listing",
         "payment", "refund", "invoice", "order", "quotation", "charges", "price", "rate", "service",
         "delivery", "stock", "call", "connect", "online", "mobile", "photo", "video"]

# Languages whose table we can review by eye, and so carry the full term list. Everything else gets the
# brand names only: they round-trip exactly everywhere, and a wrong entry is worse than no entry.
FULL = ["hi-IN", "mr-IN", "gu-IN"]
BRAND_ONLY = ["bn-IN", "te-IN", "kn-IN"]
BRANDS = ["IndiaMART", "WhatsApp"]

OVERRIDES = {
    "hi-IN": {"plan": "प्लान", "product": "प्रोडक्ट", "products": "प्रोडक्ट्स", "account": "अकाउंट",
              "number": "नंबर", "payment": "पेमेंट", "order": "ऑर्डर", "service": "सर्विस",
              "minutes": "मिनट्स", "app": "ऐप", "main": "मैं", "maine": "मैंने"},
    "mr-IN": {"plan": "प्लान", "account": "अकाउंट", "number": "नंबर", "service": "सर्विस",
              "supplier": "सप्लायर", "suppliers": "सप्लायर्स", "app": "ऐप", "main": "मैं", "maine": "मैंने"},
    "gu-IN": {},
}


def _key() -> str:
    for line in (ROOT / ".env").read_text().splitlines():
        if line.strip().startswith("SARVAM_API_KEY="):
            return line.split("=", 1)[1].strip()
    return os.environ.get("SARVAM_API_KEY", "")


def translit(key: str, text: str, src: str, tgt: str, tries: int = 6) -> str:
    for i in range(tries):
        r = requests.post(API, headers={"api-subscription-key": key, "Content-Type": "application/json"},
                          json={"input": text, "source_language_code": src, "target_language_code": tgt,
                                "spoken_form": tgt != "en-IN"}, timeout=30)
        if r.status_code == 200:
            return r.json().get("transliterated_text", "")
        if r.status_code == 429:          # shared Starter quota — back off rather than give up
            time.sleep(2.0 * (i + 1))
            continue
        return f"ERR{r.status_code}"
    return "ERR429"


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--write", action="store_true", help="rewrite gcx/pronounce.py (default: audit only)")
    a = p.parse_args()
    key = _key()
    if not key:
        sys.exit("No SARVAM_API_KEY in .env")

    jobs = [(l, t) for l in FULL for t in TERMS] + [(l, t) for l in BRAND_ONLY for t in BRANDS]
    with ThreadPoolExecutor(3) as ex:
        got = list(ex.map(lambda j: (j[0], j[1], translit(key, j[1], "en-IN", j[0])), jobs))
    tables: dict[str, dict[str, str]] = {}
    for lang, term, native in got:
        tables.setdefault(lang, {})[term.lower()] = OVERRIDES.get(lang, {}).get(term.lower(), native)

    print("auditing round-trips…")
    back = [(l, t, v, translit(key, v, l, "en-IN")) for l, tbl in tables.items() for t, v in tbl.items()]
    suspect = [(l, t, v, b) for l, t, v, b in back
               if difflib.SequenceMatcher(None, t.lower(), b.lower()).ratio() < 0.75]
    print(f"\nSUSPECT ({len(suspect)}) — check these by eye before shipping:")
    for l, t, v, b in suspect:
        print(f"  {l}  {t:13s} -> {v:18s} -> back: {b}")
    if not a.write:
        print("\n(audit only — pass --write to regenerate gcx/pronounce.py)")
        return
    for lang in FULL:
        tables[lang].update(OVERRIDES[lang])
    print(f"\n{len(tables)} tables ready; merge them into gcx/pronounce.py by hand after reading the audit.")


if __name__ == "__main__":
    main()
