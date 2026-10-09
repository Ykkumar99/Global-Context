"""Evidence for the personalised opening: IndiaMART's own personalised-script trial.

Compares lead_bot_version 'personalis…' (personalised script) with 'main_vani' using
(a) the Persona dataset's answered bot calls and (b) the Best-Time-to-Call attempts.

usage: python scripts/personalised_trial.py --persona "<Persona Files dir>" --btc "<BesTime to Call dir>"
"""
from __future__ import annotations

import argparse
import glob
import json
import math
import os
from pathlib import Path

import pandas as pd


def two_prop(x1, n1, x2, n2):
    p = (x1 + x2) / (n1 + n2)
    z = (x1 / n1 - x2 / n2) / math.sqrt(p * (1 - p) * (1 / n1 + 1 / n2))
    return round(math.erfc(abs(z) / math.sqrt(2)), 4)


def summarise(df: pd.DataFrame, label: str) -> dict:
    g = df.groupby("lead_bot_version")["meeting_fixed"].agg(["sum", "count"])
    a, b = g.loc[g.index.str.startswith("personalis")].sum(), g.loc["main_vani"]
    return {"basis": label, "personalised": {"n": int(a["count"]), "meeting_fixed_pct": round(100 * a["sum"] / a["count"], 2)},
            "main_vani": {"n": int(b["count"]), "meeting_fixed_pct": round(100 * b["sum"] / b["count"], 2)},
            "relative_lift_pct": round(100 * ((a["sum"] / a["count"]) / (b["sum"] / b["count"]) - 1), 1),
            "p_value": two_prop(a["sum"], a["count"], b["sum"], b["count"])}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--persona")
    ap.add_argument("--btc")
    ap.add_argument("--out", default="outputs/personalised_trial.json")
    a = ap.parse_args()
    res = []
    if a.persona:
        files = [f for f in glob.glob(os.path.join(a.persona, "**", "ps07_bot_calls_*.csv"), recursive=True)]
        df = pd.concat([pd.read_csv(f, usecols=["lead_bot_version", "meeting_fixed"]) for f in files])
        res.append(summarise(df, "answered VANI calls (Persona dataset, Apr–Sep 2026)"))
    if a.btc:
        f = glob.glob(os.path.join(a.btc, "**", "*Call Attempts*.csv"), recursive=True)[0]
        df = pd.read_csv(f, usecols=["lead_bot_version", "meeting_fixed"], low_memory=False).dropna()
        res.append(summarise(df, "all dial attempts (Best-Time-to-Call dataset, Apr–Sep 2026)"))
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(res, indent=2))
    print(json.dumps(res, indent=2))


if __name__ == "__main__":
    main()
