"""Q14.xx / RQ-h5-016 -- Do the agent instructions that set the factory's
rules pass those rules themselves (does CLAUDE.md/AGENTS.md follow its own
conventions)? Proxy: whether the process plugin's own repo passes the
compliance checks that apply to it, from check_results.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ingest.fleet import PLUGIN_REPO_NAME

RQ_ID = "RQ-h5-016"
QUESTION = "Do the agent instructions that set the factory's rules pass those rules themselves?"


def answer(con):
    rows = con.execute(
        "SELECT result, COUNT(*) AS n FROM knowledge.check_results WHERE repo = ? GROUP BY result", (PLUGIN_REPO_NAME,)
    ).fetchall()
    if not rows:
        return [{"note": f"no check_results rows for {PLUGIN_REPO_NAME} -- it may not be checked by the register"}]
    return [dict(r) for r in rows]


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
