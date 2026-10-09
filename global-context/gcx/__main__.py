"""Command line: python -m gcx <command>

  setup   [--data DIR]          ingest + build every file (one-shot, use this first)
  ingest  [--data DIR]          load datasets into the store
  build   [--glid N] [--role R] (re)build .md files (all, one role, or one GLID)
  show    GLID                  print a context file
  event   GLID CHANNEL TEXT     push a live event and print the refreshed file + freshness
  serve   [--port 8000]         start the API + demo UI
  eval                          run the evaluation suite -> outputs/eval_report.{json,md}
  slice   --data DIR [--n 60]   create the small demo dataset in data/demo from the full data
  segments                      WhatsApp-campaign segments read from the .md files → outputs/segments.csv
  brief   GLID                  executive call-prep page from the .md → outputs/briefs/GLID.html
  resume-eval [--n 12]          WhatsApp → voice resumption benchmark, memory on vs off
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from .config import ROOT, get_config, load_config


def _engine():
    from .engine import ContextEngine
    return ContextEngine()


def cmd_ingest(a) -> None:
    from .ingest import ingest_all
    from .store import Store
    cfg = get_config()
    data = Path(a.data) if a.data else cfg.path("data_dir")
    if not data.exists():
        sys.exit(f"Data folder not found: {data}")
    stats = ingest_all(Store(), data)
    print("Ingest done:", {k: v for k, v in stats.items()})


def cmd_build(a) -> None:
    eng = _engine()
    if a.glid:
        d = eng.build(int(a.glid))
        print(d["md"])
        print(f"[{d['tokens']} tokens · v{d['version']} · {d['build_ms']:.1f} ms]")
        return
    for role in ([a.role] if a.role else ["seller", "buyer"]):
        print(f"Building {role} files ...")
        print(" ", eng.build_all(role=role, limit=a.limit))
    print(f"Files written to {eng.out_dir}")


def cmd_show(a) -> None:
    print(_engine().get(int(a.glid))["md"])


def cmd_event(a) -> None:
    eng = _engine()
    d = eng.on_event(int(a.glid), a.channel, a.kind, a.text, {"live": 1}, enrich=False)
    print(d["md"])
    print(f"[refreshed {d['changed']} in {d['freshness_ms']} ms · v{d['version']}]")


def cmd_setup(a) -> None:
    cmd_ingest(a)
    a.glid, a.role = None, None
    cmd_build(a)


def cmd_serve(a) -> None:
    import uvicorn
    print(f"\n  Global Context demo → http://localhost:{a.port}\n")
    uvicorn.run("gcx.api:app", host=a.host, port=a.port, log_level="warning")


def cmd_eval(a) -> None:
    from .evaluate import run_all
    run_all(sample=a.sample)


def cmd_segments(a) -> None:
    from .reuse import files_from_dir, segments_csv
    cfg = get_config()
    out = cfg.path("out_dir")
    csv_text = segments_csv(files_from_dir(out / "seller_md"))
    (out / "segments.csv").write_text(csv_text, encoding="utf-8")
    print(f"{csv_text.count(chr(10)) - 1} rows → {out / 'segments.csv'}")


def cmd_brief(a) -> None:
    from .reuse import exec_brief_html
    cfg = get_config()
    d = cfg.path("out_dir") / "briefs"
    d.mkdir(parents=True, exist_ok=True)
    p = d / f"{a.glid}.html"
    p.write_text(exec_brief_html(_engine().get(int(a.glid))["md"]), encoding="utf-8")
    print(p)


def cmd_resume(a) -> None:
    import json as _j
    import shutil
    import tempfile
    from . import resume_eval
    from .engine import ContextEngine
    from .store import Store
    cfg = get_config()
    tmp = Path(tempfile.mkdtemp()) / "r.db"
    shutil.copy(cfg.path("db_path"), tmp)
    print(_j.dumps(resume_eval.run(ContextEngine(Store(tmp), write_files=False), n_sellers=a.n,
                                   out_dir=cfg.path("out_dir")), indent=1))


def cmd_slice(a) -> None:
    from .demo_slice import make_slice
    make_slice(Path(a.data), ROOT / "data" / "demo", n_random=a.n)


def main(argv=None) -> None:
    for stream in (sys.stdout, sys.stderr):  # Windows consoles default to cp1252; files contain ₹ ✓ → etc.
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(name)s: %(message)s")
    p = argparse.ArgumentParser(prog="python -m gcx", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--config", help="path to config.yaml")
    sub = p.add_subparsers(dest="cmd", required=True)
    for name in ("ingest", "setup"):
        s = sub.add_parser(name)
        s.add_argument("--data")
        s.add_argument("--limit", type=int)
    s = sub.add_parser("build"); s.add_argument("--glid"); s.add_argument("--role"); s.add_argument("--limit", type=int)
    s = sub.add_parser("show"); s.add_argument("glid")
    s = sub.add_parser("event"); s.add_argument("glid"); s.add_argument("channel"); s.add_argument("text")
    s.add_argument("--kind", default="typed")
    s = sub.add_parser("serve"); s.add_argument("--port", type=int, default=8000); s.add_argument("--host", default="0.0.0.0")
    s = sub.add_parser("eval"); s.add_argument("--sample", type=int, default=None)
    s = sub.add_parser("slice"); s.add_argument("--data", required=True); s.add_argument("--n", type=int, default=60)
    sub.add_parser("segments")
    s = sub.add_parser("brief"); s.add_argument("glid")
    s = sub.add_parser("resume-eval"); s.add_argument("--n", type=int, default=12)
    a = p.parse_args(argv)
    load_config(a.config)
    {"ingest": cmd_ingest, "build": cmd_build, "show": cmd_show, "event": cmd_event, "setup": cmd_setup,
     "serve": cmd_serve, "eval": cmd_eval, "slice": cmd_slice, "segments": cmd_segments, "brief": cmd_brief,
     "resume-eval": cmd_resume}[a.cmd](a)


if __name__ == "__main__":
    main()
