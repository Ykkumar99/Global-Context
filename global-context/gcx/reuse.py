"""Non-bot consumers of the same seller.md / buyer.md files — proof the files are a shared asset.

* parse_md()        : the file format is machine-readable (front-matter + fixed sections)
* exec_brief_html() : a printable 20-second pre-call brief for IndiaMART sales executives
* segments()        : WhatsApp-campaign / dialer segments computed by reading the .md files only
"""
from __future__ import annotations

import csv
import html
import io
import re
from pathlib import Path

SEGMENTS = {
    "open_whatsapp_question": ("WhatsApp question not yet answered on a call", r"WhatsApp .*not yet answered"),
    "asked_for_callback": ("Asked for a callback / gave a time", r"Requested a callback|asked to be called|‘call later’"),
    "unread_enquiries": ("Has unread buyer enquiries", r"new enquir(y|ies) unread"),
    "buyer_waiting_reply": ("A buyer is waiting for their reply", r"awaiting seller response"),
    "do_not_call": ("Asked not to be called — exclude from campaigns", r"⛔"),
    "wrong_number": ("Recent call reached the wrong person — verify number", r"isn't .* confirm identity"),
    "call_fatigue": ("Called 2+ times this week — rest", r"this week"),
    "met_executive": ("Already in touch with an executive", r"IndiaMART executive"),
}


def parse_md(md: str) -> dict:
    """front-matter dict + {section title: [bullets/lines]} + header lines."""
    fm, body = {}, md
    m = re.match(r"---\n(.*?)\n---\n?(.*)", md, re.S)
    if m:
        for line in m.group(1).splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                fm[k.strip()] = v.strip()
        body = m.group(2)
    sections: dict[str, list[str]] = {}
    header: list[str] = []
    cur = None
    for line in body.splitlines():
        if line.startswith("## "):
            cur = line[3:].strip()
            sections[cur] = []
        elif line.strip():
            text = re.sub(r"^[->]\s*", "", line.strip())
            (sections[cur] if cur else header).append(text)
    return {"meta": fm, "header": header, "sections": sections}


def _md_inline(s: str) -> str:
    return re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", html.escape(s))


def exec_brief_html(md: str) -> str:
    d = parse_md(md)
    sec = d["sections"]
    title = d["header"][0].lstrip("# ") if d["header"] else f"GLID {d['meta'].get('glid')}"
    facts = "".join(f"<p>{_md_inline(x)}</p>" for x in d["header"][1:])
    def block(name, label):
        items = sec.get(name) or []
        return f"<h2>{label}</h2><ul>" + "".join(f"<li>{_md_inline(x)}</li>" for x in items) + "</ul>" if items else ""
    talk = []
    for k, v in sec.items():
        if k.startswith("Open threads") or k.startswith("Before you speak"):
            talk += v
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Call prep · {html.escape(title)}</title><style>
body{{font:15px/1.5 'Hanken Grotesk',system-ui,sans-serif;color:#17213b;max-width:760px;margin:24px auto;padding:0 16px;background:#fff}}
h1{{font:700 24px/1.2 'Bricolage Grotesque',system-ui;margin:0 0 4px}} h2{{font-size:14px;margin:18px 0 4px;color:#3a4566}}
.tag{{display:inline-block;background:#fff4cf;border-radius:6px;padding:2px 8px;font-size:12px;margin-bottom:10px}}
ul{{margin:0;padding-left:20px}} .meta{{color:#6b7590;font-size:12px}} p{{margin:2px 0}}
@media print{{.tag{{border:1px solid #ccc}}}}</style></head><body>
<span class="tag">Executive call prep — generated from the same {html.escape(d['meta'].get('role', 'seller'))}.md the bot uses</span>
<h1>{html.escape(title)}</h1>{facts}
<h2>Talk about first</h2><ul>{''.join(f'<li>{_md_inline(x)}</li>' for x in talk) or '<li>No open items — start with their business pulse.</li>'}</ul>
{block('Last conversations', 'What happened recently')}
{block('Business pulse (30d | 90d)', 'Business pulse')}
{block('What they are looking for', 'What they are looking for')}
<p class="meta">GLID {html.escape(d['meta'].get('glid', ''))} · file v{html.escape(d['meta'].get('version', ''))} · as of {html.escape(d['meta'].get('as_of', ''))}</p>
</body></html>"""


def segments(files: list[tuple[int, str]]) -> dict[str, list[int]]:
    out = {k: [] for k in SEGMENTS}
    for glid, md in files:
        for k, (_label, pat) in SEGMENTS.items():
            if re.search(pat, md):
                out[k].append(glid)
    return out


def segments_csv(files: list[tuple[int, str]]) -> str:
    seg = segments(files)
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["segment", "description", "glid"])
    for k, ids in seg.items():
        for g in ids:
            w.writerow([k, SEGMENTS[k][0], g])
    return buf.getvalue()


def files_from_dir(d: Path) -> list[tuple[int, str]]:
    return [(int(p.stem), p.read_text(encoding="utf-8")) for p in sorted(d.glob("*.md")) if p.stem.isdigit()]
