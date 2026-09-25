"""Q12.xx / NEW-A-10 -- What kind of repo is the template: monorepo or
single service, and backend, frontend or both? Proxy: the template's top-
level directories touched by commits (ui/, lib/, service/, cli/, schema/
etc -- a monorepo signature) and file extensions present (go vs tsx/ts).
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ingest.fleet import TEMPLATE_REPO

RQ_ID = "NEW-A-10"
QUESTION = "What kind of repo is the template: monorepo or single service, backend/frontend/both?"


def answer(con):
    if not TEMPLATE_REPO:
        return [{"note": "no FLEET.md group: template repo in this fleet"}]
    dirs = con.execute(
        "SELECT DISTINCT top_dir FROM git.commit_files WHERE repo = ? AND top_dir != '(root)'", (TEMPLATE_REPO,)
    ).fetchall()
    exts = con.execute(
        "SELECT ext, COUNT(*) AS n FROM git.commit_files WHERE repo = ? AND ext IN "
        "('go', 'ts', 'tsx', 'js', 'jsx') GROUP BY ext ORDER BY n DESC", (TEMPLATE_REPO,)
    ).fetchall()
    langs = {r["ext"]: r["n"] for r in exts}
    return [{
        "template_repo": TEMPLATE_REPO,
        "top_level_dirs": sorted(r[0] for r in dirs),
        "language_mix": langs,
        "reads_as": ("monorepo" if len(dirs) > 3 else "few top-level modules") + ", " +
                    ("backend and frontend both" if {"go"} & langs.keys() and {"ts", "tsx"} & langs.keys()
                     else "single stack"),
    }]


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
