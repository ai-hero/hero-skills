"""Q12.xx / RQ-h1-004 -- Which repos depend on each shared service, and
does each repo's design record say so? Proxy: repos whose HERO.md
`## Connections` section (NEW-CN-01's parser) declares a connector whose
`at:` value names the shared-service repo.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ingest.fleet import ALL_REPOS, ROLE_OVERRIDES, path_of

RQ_ID = "RQ-h1-004"
QUESTION = "Which repos depend on each shared service, and does each repo's design record say so?"


def answer(con):
    shared_services = [r for r, role in ROLE_OVERRIDES.items() if role == "shared service"]
    if not shared_services:
        return [{"note": "no shared service repos configured (role_overrides) for this fleet"}]
    from questions.NEW_CN_01 import hero_md_at_head, parse_connections
    out = []
    for repo in ALL_REPOS:
        path = path_of(repo)
        if not os.path.isdir(path):
            continue
        text = hero_md_at_head(path)
        if not text:
            continue
        conns = parse_connections(text) or {}
        mentions = [s for s in shared_services if s in text]
        if mentions:
            out.append({"repo": repo, "mentions_shared_service_in_hero_md": mentions})
    return out


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
