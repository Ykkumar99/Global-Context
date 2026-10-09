"""Ingest the hackathon datasets into the context store as a unified event stream.

Seller side : the 11 ``gc_*.csv`` files (Global Context seller dataset).
Buyer side  : ``getContext`` API responses, either the raw Kibana CSV export
              (rows split across lines are re-assembled) or a ``.jsonl`` file
              with one ``{"glid":..., "ts":..., "data":{...}}`` per line.

In production these loaders are replaced by API / Kafka consumers that call
``Store.add_event`` — the rest of the pipeline is unchanged.
"""
from __future__ import annotations

import csv
import json
import os
import re
from pathlib import Path

import pandas as pd

from .store import Store

csv.field_size_limit(2**31 - 1)

SELLER_FILES = {
    "profile": "gc_seller_profile.csv",
    "enquiry": "gc_enquiries_received.csv",
    "enquiry_reply": "gc_enquiry_messages.csv",
    "buyer_call": "gc_buyer_calls_received.csv",
    "buylead": "gc_buyleads_bought.csv",
    "wa_msg": "gc_whatsapp_messages.csv",
    "wa_chat": "gc_whatsapp_chatbot_conversations.csv",
    "pns_extract": "gc_buyer_call_extractions.csv",
    "bot_call": "gc_bot_calls.csv",
    "bot_turns": "gc_bot_call_turns.csv",
    "exec_call": "gc_executive_calls.csv",
}


def _walk(data_dir: Path):
    for root, _dirs, files in os.walk(data_dir, followlinks=True):
        for f in files:
            yield Path(root) / f


def _find(data_dir: Path, name: str) -> Path | None:
    hits = sorted(p for p in _walk(data_dir) if p.name == name)
    return hits[0] if hits else None


def _ts(series: pd.Series) -> pd.Series:
    return pd.to_datetime(series, errors="coerce").dt.strftime("%Y-%m-%d %H:%M:%S")


def _nz(v):
    if v is None:
        return None
    try:
        if pd.isna(v):
            return None
    except (TypeError, ValueError):
        pass
    if isinstance(v, float) and v.is_integer():
        return int(v)
    return v


def _records(df: pd.DataFrame, cols: list[str]) -> list[dict]:
    sub = df[[c for c in cols if c in df.columns]]
    return [{k: _nz(v) for k, v in r.items() if _nz(v) is not None} for r in sub.to_dict("records")]


_KW_SUFFIX = re.compile(r"_p\d+.*$")


def ingest_sellers(store: Store, data_dir: Path, log=print) -> dict:
    stats: dict[str, int] = {}
    read = lambda key: pd.read_csv(_find(data_dir, SELLER_FILES[key]), low_memory=False)  # noqa: E731

    # ---- profiles
    prof_path = _find(data_dir, SELLER_FILES["profile"])
    if not prof_path:
        log(f"  ! no {SELLER_FILES['profile']} under {data_dir}")
        return stats
    prof = pd.read_csv(prof_path, low_memory=False)
    store.put_profiles((int(r["fk_glusr_usr_id"]), "seller", {k: _nz(v) for k, v in r.items() if _nz(v) is not None})
                       for r in prof.to_dict("records"))
    stats["profiles"] = len(prof)
    known = set(prof.fk_glusr_usr_id.astype(int))

    def emit(key, df, glid_col, ts_col, channel, kind_col, text_col, meta_cols):
        df = df[df[glid_col].notna()].copy()
        df[glid_col] = df[glid_col].astype("int64")
        df = df[df[glid_col].isin(known)]
        df["_ts"] = _ts(df[ts_col])
        df = df[df["_ts"].notna()]
        kinds = df[kind_col].astype(str).tolist() if kind_col else [None] * len(df)
        texts = df[text_col].tolist() if text_col else [None] * len(df)
        metas = _records(df, meta_cols)
        rows = [(int(g), ts, channel, k, None if t is None or (isinstance(t, float) and pd.isna(t)) else str(t), m, 0)
                for g, ts, k, t, m in zip(df[glid_col], df["_ts"], kinds, texts, metas)]
        store.add_events(rows)
        stats[channel] = len(rows)
        log(f"  {channel:<14} {len(rows):>8,} events")

    files = {k: _find(data_dir, v) for k, v in SELLER_FILES.items()}

    if files["enquiry"]:
        emit("enquiry", read("enquiry"), "seller_glid", "enquiry_date", "enquiry", "source_module", "message",
             ["query_id", "subject", "product_name", "buyer_city", "buyer_state", "buyer_company", "buyer_designation",
              "first_read_date", "mcat_id", "search_keyword"])
    if files["enquiry_reply"]:
        emit("enquiry_reply", read("enquiry_reply"), "seller_glid", "reply_date", "enquiry_reply", "message_from",
             "reply_text", ["query_id", "subject", "sequence", "template_flag", "first_read_date"])
    if files["buyer_call"]:
        emit("buyer_call", read("buyer_call"), "seller_glid", "call_datetime", "buyer_call", "call_status", None,
             ["talk_sec", "duration_sec", "caller_circle", "mcat_id", "buyer_glid"])
    if files["buylead"]:
        bl = read("buylead")
        bl["keyword"] = bl["keyword"].astype(str).str.replace(_KW_SUFFIX, "", regex=True).replace("nan", None)
        emit("buylead", bl, "seller_glid", "purchase_date", "buylead", "purchase_mode", "keyword",
             ["credits_used", "module", "mcat_rank", "distance_city", "buylead_id"])
    if files["wa_msg"]:
        emit("wa_msg", read("wa_msg"), "glid", "entry_date", "wa_msg", "message_sender", None,
             ["message_status", "campaign_name", "source", "read_at"])
    if files["wa_chat"]:
        emit("wa_chat", read("wa_chat"), "glid", "entry_date", "wa_chat", "action_type", "user_message",
             ["bot_reply", "intent", "source", "session_id"])
    if files["pns_extract"]:
        emit("pns_extract", read("pns_extract"), "glid", "call_date", "pns_extract", "seller_role_on_call",
             "products_discussed", ["categories", "prices_quoted", "specs_discussed", "stock_status",
                                    "file_intent", "languages", "file_duration_sec"])
    if files["bot_call"]:
        bc = read("bot_call")
        if files["bot_turns"]:
            turns = pd.read_csv(files["bot_turns"]).sort_values(["attempt_id", "turn_no"])
            tmap = {a: [[s, str(t)] for s, t in zip(g.speaker, g.text)] for a, g in turns.groupby("attempt_id")}
            bc["turns"] = bc["attempt_id"].map(tmap)
        emit("bot_call", bc, "fk_glusr_usr_id", "call_start_time", "bot_call", "disposition_label",
             "lead_call_summary", ["attempt_id", "lead_call_duration", "lead_bot_version", "redis_bucket",
                                   "call_attempt_count", "meeting_fixed", "turns"])
    if files["exec_call"]:
        emit("exec_call", read("exec_call"), "fk_glusr_usr_id", "call_start_time", "exec_call", "status", None,
             ["module", "call_duration", "call_duration_customer", "fk_employeeid"])
    return stats


# ------------------------------------------------------------------ buyers
def _reassemble_kibana_csv(path: Path) -> list[dict]:
    """The provided export splits long responses across physical rows; stitch them."""
    recs: list[dict] = []
    with path.open(encoding="utf-8", newline="") as fh:
        rows = csv.reader(fh)
        next(rows, None)
        cur = None
        for r in rows:
            if r and r[0].strip():
                cur = {"ts": r[0], "code": r[1] if len(r) > 1 else "", "glid": r[2] if len(r) > 2 else "",
                       "resp": r[6] if len(r) > 6 else ""}
                recs.append(cur)
            elif cur is not None:
                cur["resp"] += "".join(c for c in r if c)
    out = []
    for x in recs:
        try:
            inner = json.loads(json.loads(x["resp"])["API_RESPONSE_JSON"])
            data = inner["data"]
            ts = pd.to_datetime(x["ts"].replace(" @ ", " "), errors="coerce")
            out.append({"glid": int(data.get("glid") or data["kycdetails"]["glid"]), "data": data,
                        "ts": "" if pd.isna(ts) else ts.isoformat()})
        except Exception:  # truncated / error responses are skipped
            continue
    return out


def load_buyer_contexts(data_dir: Path) -> list[dict]:
    items: list[dict] = []
    for p in sorted(x for x in _walk(data_dir) if x.suffix == ".jsonl"):
        if "buyer" in p.name.lower():
            items += [json.loads(line) for line in p.read_text(encoding="utf-8").splitlines() if line.strip()]
    for p in sorted(x for x in _walk(data_dir) if x.suffix == ".csv"):
        # the official export is "..._Buyer Side.csv" (space); accept space / hyphen / underscore
        name = re.sub(r"[\s\-]+", "_", p.name.lower())
        if "buyer_side" in name or "getcontext" in name:
            items += _reassemble_kibana_csv(p)
    latest: dict[int, dict] = {}
    for it in items:  # keep one (latest by timestamp) snapshot per GLID
        g = int(it["glid"])
        if g not in latest or str(it.get("ts", "")) >= str(latest[g].get("ts", "")):
            latest[g] = it
    return list(latest.values())


def ingest_buyers(store: Store, data_dir: Path, log=print) -> int:
    items = load_buyer_contexts(data_dir)
    store.put_profiles((it["glid"], "buyer", it["data"]) for it in items)
    log(f"  buyer getContext snapshots {len(items):>5,}")
    return len(items)


def ingest_all(store: Store, data_dir: Path, reset: bool = True, log=print) -> dict:
    if reset:
        store.reset()
    log(f"Ingesting from {data_dir}")
    stats = ingest_sellers(store, data_dir, log)
    stats["buyers"] = ingest_buyers(store, data_dir, log)
    store.set_meta("ingest_stats", stats)
    store.set_meta("ingest_dir", Path(data_dir).as_posix())
    return stats
