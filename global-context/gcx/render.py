"""Assemble sections into a compact markdown file under a hard token budget."""
from __future__ import annotations

from datetime import datetime

from .textutil import est_tokens, resolve_times

# lower number = more important; trimmed last
PRIORITY = {"header": 0, "guardrails": 1, "opening": 2, "threads": 3, "wants": 3, "recent": 4,
            "pulse": 5, "signals": 5, "engagement": 6}


def frontmatter(glid: int, role: str, as_of: datetime, version: int, sources: dict[str, int],
                llm: bool) -> str:
    src = ", ".join(f"{k}:{v}" for k, v in sorted(sources.items(), key=lambda x: -x[1]) if v)
    return (f"---\nglid: {glid}\nrole: {role}\nas_of: {as_of:%Y-%m-%d %H:%M}\nversion: {version}\n"
            f"llm_enriched: {str(llm).lower()}\nsources: {src or 'profile'}\n---")


def assemble(sections: dict[str, list[str]], order: list[str], titles: dict[str, str],
             budget: int, fm: str, now: datetime | None = None) -> tuple[str, int, list[str]]:
    """Render; if over budget drop bullets from the least important sections first."""
    now = now or datetime.now()
    secs = {k: [resolve_times(x, now) for x in v] for k, v in sections.items() if v}
    dropped: list[str] = []

    def render() -> str:
        parts = [fm]
        for name in order:
            lines = secs.get(name)
            if not lines:
                continue
            if name == "header":
                parts.append("\n".join(lines))
            elif name == "opening":
                parts.append(f"## {titles[name]}\n> {lines[0]}")
            else:
                parts.append(f"## {titles[name]}\n" + "\n".join(f"- {x}" for x in lines))
        return "\n\n".join(parts) + "\n"

    md = render()
    while est_tokens(md) > budget:
        cands = [n for n in secs if n not in ("header", "opening") and secs[n]]
        if not cands:
            break
        worst = max(cands, key=lambda n: (PRIORITY.get(n, 9), len(secs[n])))
        dropped.append(f"{worst}:{secs[worst].pop()[:30]}")
        if not secs[worst]:
            del secs[worst]
        md = render()
    return md, est_tokens(md), dropped
