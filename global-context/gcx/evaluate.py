"""Evaluation suite -> outputs/eval_report.{json,md}

1. Compactness & structure  : tokens per file, compression vs raw source data, schema validity
2. Freshness (replay)       : hold out the last days of real events, replay them one by one
                              through the incremental engine, measure event->file latency
3. Consistency              : incrementally refreshed files vs a full rebuild at the same instant
4. Business impact          : point-in-time context for every real VANI call (no future data):
                              how often the bot started cold although memory had something to say,
                              how outcomes differ when memory flags were present, and whether the
                              sellers' "I already told you"-type pushback was predictable from memory
"""
from __future__ import annotations

import json
import math
import re
import shutil
import statistics as st
import tempfile
import time
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path

from . import seller_sections as S
from .config import get_config
from .engine import ContextEngine
from .store import Store, parse_ts, to_ts

REQUIRED = {"seller": ["# ", "## Suggested opening"], "buyer": ["# ", "## Suggested opening"]}
REDUNDANT = re.compile(
    r"(mil (?:chuke|liya|gaye|ke gaye)|meeting ho (?:gayi|chuki)|baat ho (?:gayi|chuki)|pehle (?:se|bhi|hi) "
    r"(?:baat|call|bata|mil)|already|kitni baar|baar baar|phir se call|dobara call|abhi (?:to|toh) call (?:aaya|kiya)|"
    r"executive (?:se|ne|aaye|aaya|mil)|wrong number|galat number|(?:ye|yeh) .{0,25} nahi hai|membership (?:chaalu|chalu|hai)|"
    r"paid (?:member|membership|service) (?:hai|chaalu|chalu|le))", re.I)


def pctl(xs, p):
    xs = sorted(xs)
    return round(xs[min(len(xs) - 1, int(p * len(xs)))], 2) if xs else None


def two_prop(x1, n1, x2, n2):
    if not n1 or not n2:
        return None
    p = (x1 + x2) / (n1 + n2)
    se = math.sqrt(p * (1 - p) * (1 / n1 + 1 / n2)) or 1e-9
    z = (x1 / n1 - x2 / n2) / se
    return round(math.erfc(abs(z) / math.sqrt(2)), 4)


# --------------------------------------------------------------- 1. compact
def eval_compactness(eng: ContextEngine) -> dict:
    out = {}
    c = eng.store.conn()
    for role in ("seller", "buyer"):
        rows = c.execute("SELECT glid, md, tokens FROM docs WHERE role=?", (role,)).fetchall()
        if not rows:
            continue
        toks = [r["tokens"] for r in rows]
        valid = sum(1 for r in rows if all(k in r["md"] for k in REQUIRED[role]) and r["md"].startswith("---")
                    and r["tokens"] <= eng.budget + 5)
        ratios, raw_tok = [], []
        for r in rows:
            prof = c.execute("SELECT data FROM profiles WHERE glid=?", (r["glid"],)).fetchone()[0]
            raw = len(prof)
            if role == "seller":
                raw += c.execute("SELECT COALESCE(SUM(LENGTH(text)+LENGTH(meta)+40),0) FROM events WHERE glid=? "
                                 "AND live=0", (r["glid"],)).fetchone()[0]
            raw_tok.append(raw / 4)
            ratios.append((raw / 4) / max(1, r["tokens"]))
        generic = sum(1 for r in rows if re.search(
            r"(do minute baat karni thi|Aapko kis product ki zaroorat|enquiries badhane mein madad|account ke baare)", r["md"]))
        secs = Counter(h for r in rows for h in re.findall(r"^## (.+)$", r["md"], re.M))
        out[role] = {
            "files": len(rows), "tokens_median": st.median(toks), "tokens_p95": pctl(toks, .95), "tokens_max": max(toks),
            "raw_source_tokens_median": round(st.median(raw_tok)), "compression_median": round(st.median(ratios), 1),
            "schema_valid_pct": round(100 * valid / len(rows), 1),
            "personalised_opening_pct": round(100 * (1 - generic / len(rows)), 1),
            "section_coverage_pct": {k: round(100 * v / len(rows), 1) for k, v in secs.most_common()},
        }
    return out


# ------------------------------------------------------------- privacy
def eval_privacy(eng: ContextEngine) -> dict:
    """Cross-party check: no quoted text in a seller file may contain a buyer's personal name, and no file
    may contain a phone number or email."""
    from .textutil import counterpart_names
    c = eng.store.conn()
    names: dict[int, set] = {}
    for g, m in c.execute("SELECT glid, meta FROM events WHERE channel IN ('enquiry','enquiry_reply')"):
        names.setdefault(g, set()).update(counterpart_names([json.loads(m or "{}").get("subject")]))
    rows = c.execute("SELECT glid, role, md FROM docs").fetchall()
    leaks, pii = 0, 0
    for r in rows:
        md = r["md"]
        if re.search(r"(?<!\d)[6-9]\d{9}(?!\d)|[\w.+-]+@[\w-]+\.[\w.]+", md):
            pii += 1
        quoted = " ".join(re.findall(r"“([^”]*)”", md)).lower()
        if any(len(n) >= 4 and re.search(rf"\b{re.escape(n)}\b", quoted) for n in names.get(r["glid"], ())):
            leaks += 1
    return {"files_checked": len(rows), "files_quoting_other_party_name": leaks, "files_with_phone_or_email": pii,
            "counterpart_names_known": int(sum(len(v) for v in names.values()))}


# ------------------------------------------------- 2+3. freshness / replay
def eval_freshness(eng: ContextEngine, days: int = 3, max_events: int = 3000) -> dict:
    tmp = Path(tempfile.mkdtemp()) / "replay.db"
    shutil.copy(eng.store.path, tmp)
    store = Store(tmp)
    end = store.max_event_ts()
    t0 = end - timedelta(days=days)
    c = store.conn()
    held = [dict(r) for r in c.execute(
        "SELECT * FROM events WHERE ts>? AND live=0 ORDER BY ts, id", (to_ts(t0),))]
    held = held[-max_events:] if len(held) > max_events else held
    ids = [h["id"] for h in held]
    c.executemany("DELETE FROM events WHERE id=?", [(i,) for i in ids])
    c.execute("DELETE FROM docs"); c.execute("DELETE FROM sections"); c.commit()
    rep = ContextEngine(store, write_files=False)
    first_ts = parse_ts(held[0]["ts"]) if held else t0
    for g in {h["glid"] for h in held}:  # files as they were before the replay window
        if rep.role(g) == "seller":
            rep.build_seller(g, now=first_ts)
    lat, per_ch = [], defaultdict(list)
    sec_counts = Counter()
    for h in held:
        if rep.role(h["glid"]) != "seller":
            continue
        ts = parse_ts(h["ts"])
        t = time.perf_counter()
        d = rep.on_event(h["glid"], h["channel"], h["kind"], h["text"], json.loads(h["meta"] or "{}"),
                         enrich=False, at=ts)
        ms = (time.perf_counter() - t) * 1000
        lat.append(ms)
        per_ch[h["channel"]].append(ms)
        sec_counts[len(d["changed"])] += 1
    # consistency: event-driven sections must equal a full rebuild at the same instant
    glids = sorted({h["glid"] for h in held if rep.role(h["glid"]) == "seller"})
    same, total, diffs = 0, 0, Counter()
    for g in glids[:800]:
        last = max(parse_ts(h["ts"]) for h in held if h["glid"] == g)
        inc = {k: v for k, v in store.sections(g).items() if k in ("threads", "recent", "opening", "header")}
        full_ctx = rep._seller_ctx(g, last, False, None)
        full = {"threads": S.build_threads(full_ctx), "recent": S.build_recent(full_ctx),
                "opening": [S.opening_line(full_ctx)], "header": S.build_header(full_ctx)}
        for k, v in full.items():
            total += 1
            if json.loads(inc.get(k, "[]")) == v:
                same += 1
            else:
                diffs[k] += 1
    # full rebuild throughput (nightly sweep)
    t = time.perf_counter()
    sweep = store.glids("seller")
    for g in sweep:
        rep.build_seller(g, now=end)
    sweep_s = time.perf_counter() - t
    shutil.rmtree(tmp.parent, ignore_errors=True)
    return {
        "replayed_events": len(lat), "window_days": days, "sellers_touched": len(glids),
        "latency_ms": {"p50": pctl(lat, .5), "p95": pctl(lat, .95), "p99": pctl(lat, .99), "max": pctl(lat, 1.0)},
        "latency_ms_by_channel_p50": {k: pctl(v, .5) for k, v in sorted(per_ch.items())},
        "sections_changed_per_event": dict(sorted(sec_counts.items())),
        "consistency_event_driven_sections_pct": round(100 * same / max(1, total), 2),
        "consistency_mismatch_by_section": dict(diffs),
        "full_rebuild": {"sellers": len(sweep), "seconds": round(sweep_s, 2),
                         "ms_per_seller": round(1000 * sweep_s / max(1, len(sweep)), 2)},
    }


# ------------------------------------------------------- 4. business impact
CROSS = {"wa_chat": lambda e: e["kind"] == "typed", "enquiry": lambda e: True, "enquiry_reply": lambda e: True,
         "buyer_call": lambda e: e["kind"] == "Connected", "buylead": lambda e: True,
         "exec_call": lambda e: e["kind"] == "Answered", "pns_extract": lambda e: True}


def eval_impact(eng: ContextEngine, sample: int | None = None) -> dict:
    c = eng.store.conn()
    calls = [dict(r) for r in c.execute("SELECT * FROM events WHERE channel='bot_call' AND live=0 ORDER BY ts")]
    if sample:
        calls = calls[:: max(1, len(calls) // sample)]
    n = len(calls)
    cross7, cross_any = 0, 0
    flags = Counter()
    outcome = defaultdict(lambda: [0, 0, 0])  # [calls, meeting, not_interested]
    pushback, pushback_known, transcripts = 0, 0, 0
    examples = []
    cold_open_specific = 0
    for call in calls:
        g, ts = call["glid"], parse_ts(call["ts"])
        before = ts - timedelta(minutes=1)
        prof = eng.store.profile(g)[1]
        evs = eng.store.events(g, before, since=before - timedelta(days=90))
        ctx = S.Ctx(g, prof, evs, before, eng.cfg, strict_pit=True)
        recent7 = [e for e in evs if e["ts"] >= before - timedelta(days=7) and e["channel"] in CROSS
                   and CROSS[e["channel"]](e)]
        if recent7:
            cross7 += 1
        if any(e["channel"] in CROSS for e in evs):
            cross_any += 1
        guard = S.build_guardrails(ctx)
        threads = S.open_threads(ctx)
        f = set()
        if any("executive" in x for x in guard):
            f.add("met_or_in_touch_with_executive")
        if any("this week" in x for x in guard):
            f.add("called_2plus_times_this_week")
        if any("isn't" in x for x in guard):
            f.add("wrong_number_on_recent_call")
        for t in threads:
            f.add("open_thread:" + t["type"])
        if recent7:
            f.add("cross_channel_activity_7d")
        if not S.opening_line(ctx).endswith(("do minute baat karni thi.", "baat karni thi.")):
            cold_open_specific += 1
        if f & {"called_2plus_times_this_week", "wrong_number_on_recent_call"}:
            f.add("SUPPRESS: fatigue or wrong number")
        if f & {"open_thread:wa_callback", "open_thread:wa_question", "open_thread:meeting"}:
            f.add("PRIORITISE: seller-initiated thread")
        for k in f | {"ALL"}:
            o = outcome[k]
            o[0] += 1
            o[1] += call["kind"] == "Meeting Fixed"
            o[2] += call["kind"] == "Not Interested"
        if any(x.startswith(("met", "called", "wrong", "open_thread")) for x in f):
            flags["calls_with_actionable_flag"] += 1
        meta = json.loads(call["meta"] or "{}")
        turns = meta.get("turns") or []
        if turns:
            transcripts += 1
            said = [t[1] for t in turns if t[0] == "seller" and REDUNDANT.search(str(t[1]))]
            if said:
                pushback += 1
                known = bool(f & {"met_or_in_touch_with_executive", "called_2plus_times_this_week",
                                  "wrong_number_on_recent_call", "cross_channel_activity_7d"}) or any(
                    x.startswith("open_thread") for x in f)
                pushback_known += known
                if len(examples) < 6:
                    examples.append({"glid": g, "seller_said": said[0][:140], "memory_had": sorted(f)[:4],
                                     "disposition": call["kind"]})
    base = outcome["ALL"]
    rate = lambda o, i: round(100 * o[i] / o[0], 1) if o[0] else None  # noqa: E731
    by_flag = {k: {"calls": o[0], "meeting_fixed_pct": rate(o, 1), "not_interested_pct": rate(o, 2),
                   "p_vs_rest_meeting": two_prop(o[1], o[0], base[1] - o[1], base[0] - o[0]) if k != "ALL" else None}
               for k, o in sorted(outcome.items(), key=lambda x: -x[1][0])}
    sup = outcome["SUPPRESS: fatigue or wrong number"]
    rest_n, rest_m = base[0] - sup[0], base[1] - sup[1]
    realloc = None
    if sup[0] and rest_n:
        rest_rate = rest_m / rest_n
        lost = sup[1]
        gained = sup[0] * rest_rate
        realloc = {"calls_suppressed": sup[0], "calls_suppressed_pct": round(100 * sup[0] / base[0], 1),
                   "meetings_lost": lost, "meetings_from_reallocated_capacity": round(gained),
                   "net_meeting_lift_pct": round(100 * (gained - lost) / base[1], 1),
                   "assumption": "freed dial capacity goes to sellers without these flags at their average meeting rate"}
    return {
        "vani_calls_analysed": n,
        "capacity_reallocation_estimate": realloc,
        "cold_start_with_cross_channel_activity_7d_pct": round(100 * cross7 / n, 1) if n else None,
        "cold_start_with_any_history_90d_pct": round(100 * cross_any / n, 1) if n else None,
        "calls_with_actionable_memory_flag_pct": round(100 * flags["calls_with_actionable_flag"] / n, 1) if n else None,
        "specific_personalised_opening_possible_pct": round(100 * cold_open_specific / n, 1) if n else None,
        "outcomes_by_memory_flag": by_flag,
        "transcripts_checked": transcripts,
        "seller_redundancy_pushback_calls": pushback,
        "pushback_predictable_from_memory": pushback_known,
        "pushback_predictable_pct": round(100 * pushback_known / pushback, 1) if pushback else None,
        "pushback_examples": examples,
    }


# --------------------------------------------------------------- report
def write_report(res: dict, out: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)
    (out / "eval_report.json").write_text(json.dumps(res, indent=2, default=str), encoding="utf-8")
    L = ["# Global Context — evaluation report", f"_Generated {datetime.now():%Y-%m-%d %H:%M} on dataset "
         f"`{res['dataset']}`_", ""]
    for role, r in res["compactness"].items():
        L += [f"## Compactness — {role}.md ({r['files']:,} files)",
              f"- Median **{r['tokens_median']:.0f} tokens** (p95 {r['tokens_p95']:.0f}, hard cap {res['token_budget']})",
              f"- Raw source data per user: median {r['raw_source_tokens_median']:,} tokens → "
              f"**{r['compression_median']}× compression**",
              f"- Schema-valid files: {r['schema_valid_pct']}% · opening references a specific recent event: "
              f"{r['personalised_opening_pct']}% (all others: name + category + city)",
              "- Section coverage: " + ", ".join(f"{k} {v}%" for k, v in r["section_coverage_pct"].items()), ""]
    pv = res.get("privacy")
    if pv:
        L += ["## Privacy (cross-party)", f"- {pv['files_checked']:,} files checked against "
              f"{pv['counterpart_names_known']:,} known buyer names: **{pv['files_quoting_other_party_name']} quote another "
              f"party's name**, **{pv['files_with_phone_or_email']} contain a phone number or email**", ""]
    f = res.get("freshness")
    if f:
        L += [f"## Freshness — replay of the last {f['window_days']} days ({f['replayed_events']:,} real events, "
              f"{f['sellers_touched']:,} sellers)",
              f"- Event → updated file: **p50 {f['latency_ms']['p50']} ms, p95 {f['latency_ms']['p95']} ms**, "
              f"p99 {f['latency_ms']['p99']} ms",
              f"- Incremental vs full rebuild (event-driven sections identical): "
              f"**{f['consistency_event_driven_sections_pct']}%**",
              f"- Full rebuild of {f['full_rebuild']['sellers']:,} sellers: {f['full_rebuild']['seconds']} s "
              f"({f['full_rebuild']['ms_per_seller']} ms/seller)", ""]
    rz = res.get("resumption")
    if rz:
        on, off = rz["memory_on"], rz["memory_off"]
        L += [f"## Conversations resumed without re-asking — {rz['scenarios']} WhatsApp → voice scenarios ({rz['engine']})",
              "| | Memory on | Memory off (today) |", "|---|---|---|",
              f"| Call picks up the WhatsApp thread | **{on['resumed_pct']}%** | {off['resumed_pct']}% |",
              f"| Calls where the bot re-asks a given fact | **{on['calls_with_a_re_ask_pct']}%** | {off['calls_with_a_re_ask_pct']}% |",
              f"| Given facts re-asked | **{on['facts_re_asked_pct']}%** | {off['facts_re_asked_pct']}% |", ""]
    i = res.get("impact")
    if i:
        L += [f"## Business impact — {i['vani_calls_analysed']:,} real VANI calls, context rebuilt as of 1 min before each call",
              f"- **{i['cold_start_with_cross_channel_activity_7d_pct']}%** of calls happened within 7 days of the seller's "
              f"activity on another channel — and today all of them started cold",
              f"- {i['calls_with_actionable_memory_flag_pct']}% had an actionable memory flag (open thread, executive "
              f"contact, wrong number, repeated calls)",
              f"- {i['specific_personalised_opening_possible_pct']}% could open with a specific, personal reference",
              (f"- Skipping/rescheduling calls memory flags as fatigued or wrong-number ({i['capacity_reallocation_estimate']['calls_suppressed_pct']}% of dials, "
               f"{i['capacity_reallocation_estimate']['meetings_lost']} meetings) and redeploying that capacity: "
               f"**+{i['capacity_reallocation_estimate']['net_meeting_lift_pct']}% meetings at the same call volume** (estimate)"
               if i.get("capacity_reallocation_estimate") else "- (no reallocation estimate)"),
              f"- Seller pushback like “already met / already told you / wrong number”: {i['seller_redundancy_pushback_calls']} "
              f"of {i['transcripts_checked']} transcripts; **{i['pushback_predictable_pct']}% predictable from memory**", "",
              "| Memory flag at call time | Calls | Meeting fixed | Not interested | p (meeting vs rest) |",
              "|---|---|---|---|---|"]
        for k, v in i["outcomes_by_memory_flag"].items():
            L.append(f"| {k} | {v['calls']:,} | {v['meeting_fixed_pct']}% | {v['not_interested_pct']}% | "
                     f"{v['p_vs_rest_meeting'] if v['p_vs_rest_meeting'] is not None else '–'} |")
        L.append("")
        if i["pushback_examples"]:
            L += ["**Pushback examples (seller's words) and what memory already knew:**", ""]
            for e in i["pushback_examples"]:
                L.append(f"- “{e['seller_said']}” → memory: {', '.join(e['memory_had']) or '—'} ({e['disposition']})")
    (out / "eval_report.md").write_text("\n".join(L) + "\n", encoding="utf-8")


def run_all(sample: int | None = None) -> dict:
    cfg = get_config()
    eng = ContextEngine(write_files=False)
    t = time.time()
    print("1/4 compactness & structure ...")
    res = {"dataset": eng.store.get_meta("ingest_dir") or str(cfg.data_dir), "token_budget": eng.budget, "compactness": eval_compactness(eng),
           "privacy": eval_privacy(eng)}
    print("2/4 freshness replay ...")
    res["freshness"] = eval_freshness(eng)
    print("3/4 business impact (point-in-time) ...")
    res["impact"] = eval_impact(eng, sample)
    print("4/4 resumption benchmark (WhatsApp → voice, memory on vs off) ...")
    from . import resume_eval
    tmp = Path(tempfile.mkdtemp()) / "resume.db"
    shutil.copy(eng.store.path, tmp)
    res["resumption"] = resume_eval.run(ContextEngine(Store(tmp), write_files=False), n_sellers=12,
                                        out_dir=cfg.path("out_dir"))
    shutil.rmtree(tmp.parent, ignore_errors=True)
    res["runtime_s"] = round(time.time() - t, 1)
    out = cfg.path("out_dir")
    write_report(res, out)
    print((out / "eval_report.md").read_text(encoding="utf-8"))
    return res
