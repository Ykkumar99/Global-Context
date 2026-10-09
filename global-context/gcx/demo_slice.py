"""Cut a small, portable demo dataset from the full hackathon data.

Keeps featured sellers (each shows a different memory scenario) + N random
sellers with all their events, and every buyer getContext snapshot with
emails / phone numbers removed. Output: data/demo/ (a few MB).
"""
from __future__ import annotations

import json
import random
from pathlib import Path

import pandas as pd

from .buyer_sections import strip_pii
from .ingest import SELLER_FILES, _find, load_buyer_contexts
from .textutil import mask_pii

FEATURED_SELLERS = [
    146010610,  # WhatsApp question still open + meeting fixed earlier
    79859904,   # met an executive 10 days ago, buys leads, also sources as buyer
    148480662,  # asked for a callback, enquiries unread, buyer waiting for reply
    94579284,   # do-not-call + wrong-number + speaks Gujarati
    187887068,  # called 3x this week by VANI (fatigue)
    95568576,   # very active: 175 enquiries, 90 buy-leads
    96255123,   # executive call 2 days ago
]
FEATURED_BUYERS = [73699779, 10041784, 12074600, 133846174]
GLID_COL = {"profile": "fk_glusr_usr_id", "enquiry": "seller_glid", "enquiry_reply": "seller_glid",
            "buyer_call": "seller_glid", "buylead": "seller_glid", "wa_msg": "glid", "wa_chat": "glid",
            "pns_extract": "glid", "bot_call": "fk_glusr_usr_id", "bot_turns": "fk_glusr_usr_id",
            "exec_call": "fk_glusr_usr_id"}
TEXT_COLS = ["message", "reply_text", "user_message", "bot_reply", "lead_call_summary", "text", "subject"]


def make_slice(full: Path, out: Path, n_random: int = 60, seed: int = 7) -> None:
    out.mkdir(parents=True, exist_ok=True)
    prof = pd.read_csv(_find(full, SELLER_FILES["profile"]), low_memory=False)
    rng = random.Random(seed)
    pool = [g for g in prof.fk_glusr_usr_id.astype(int) if g not in FEATURED_SELLERS]
    keep = set(FEATURED_SELLERS) | set(rng.sample(pool, min(n_random, len(pool))))
    for key, fname in SELLER_FILES.items():
        src = _find(full, fname)
        if not src:
            continue
        df = pd.read_csv(src, low_memory=False)
        df = df[df[GLID_COL[key]].isin(keep)]
        for c in TEXT_COLS:
            if c in df.columns:
                df[c] = df[c].map(lambda v: mask_pii(v) if isinstance(v, str) else v)
        if "call_recording_url" in df.columns:
            df = df.drop(columns=["call_recording_url"])
        df.to_csv(out / fname, index=False)
        print(f"  {fname:<42} {len(df):>7,} rows")
    buyers = load_buyer_contexts(full)
    with (out / "buyer_getcontext.jsonl").open("w", encoding="utf-8") as fh:
        for b in buyers:
            fh.write(json.dumps({"glid": b["glid"], "data": strip_pii(b["data"])}, ensure_ascii=False) + "\n")
    print(f"  buyer_getcontext.jsonl                     {len(buyers):>7,} buyers (PII stripped)")
    (out / "featured.json").write_text(json.dumps({"seller": FEATURED_SELLERS, "buyer": FEATURED_BUYERS}, indent=1))
    print(f"Demo slice written to {out} ({len(keep)} sellers)")
