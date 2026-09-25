"""Q6.xx / NEW-CN-01 -- Which connectors does each repo declare (design,
design system, template, architecture, ...), and what type/reach does each
carry?

Not a cube query: reads each repo's live HERO.md `## Connections` section
(git show HEAD:HERO.md) and parses the `### <kind>` sub-blocks per
docs/CONNECTIONS.md's own format -- no block means nobody looked, `type: none`
means looked and found none, per AGENTS.md's own three-state rule.
"""
import os, re, subprocess, sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ingest.fleet import ALL_REPOS, path_of

RQ_ID = "NEW-CN-01"
QUESTION = "Which connectors does each repo declare, and what type/reach does each carry?"

SECTION_RE = re.compile(r"^## Connections\s*$", re.M)
SUBSECTION_RE = re.compile(r"^### (\S+)\s*$", re.M)


def hero_md_at_head(path):
    p = subprocess.run(["git", "-C", path, "show", "HEAD:HERO.md"], capture_output=True, text=True)
    return p.stdout if p.returncode == 0 else None


def parse_connections(text):
    m = SECTION_RE.search(text)
    if not m:
        return None  # no ## Connections section at all
    rest = text[m.end():]
    next_h2 = re.search(r"^## ", rest, re.M)
    block = rest[:next_h2.start()] if next_h2 else rest
    out = {}
    subs = list(SUBSECTION_RE.finditer(block))
    for i, sm in enumerate(subs):
        kind = sm.group(1)
        body = block[sm.end():subs[i + 1].start() if i + 1 < len(subs) else len(block)]
        type_m = re.search(r"^- type:\s*(\S+)", body, re.M)
        reach_m = re.search(r"^- reach:\s*(\S+)", body, re.M)
        out[kind] = {"type": type_m.group(1) if type_m else None,
                     "reach": reach_m.group(1) if reach_m else None}
    return out


def answer(con=None):
    out = []
    for repo in ALL_REPOS:
        path = path_of(repo)
        if not os.path.isdir(path):
            continue
        text = hero_md_at_head(path)
        if text is None:
            out.append({"repo": repo, "has_hero_md": False})
            continue
        conns = parse_connections(text)
        if conns is None:
            out.append({"repo": repo, "has_hero_md": True, "has_connections_section": False})
            continue
        for kind, meta in conns.items():
            out.append({"repo": repo, "connector": kind, **meta})
        if not conns:
            out.append({"repo": repo, "has_hero_md": True, "has_connections_section": True, "connectors": "none declared"})
    return out


if __name__ == "__main__":
    for row in answer():
        print(row)
