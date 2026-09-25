"""Q11.xx / RQ-h3-006 -- Of the defects found in a clone, what share
originated in code the agent wrote versus inherited from the template?
Proxy: bug-type items whose title/log mentions the template, versus not.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ingest.fleet import TEMPLATE_REPO

RQ_ID = "RQ-h3-006"
QUESTION = "Of the defects found in a clone, what share originated in inherited template code versus agent-written code?"


def answer(con):
    if not TEMPLATE_REPO:
        return [{"note": "no FLEET.md group: template repo in this fleet"}]
    rows = con.execute(
        "SELECT title FROM plans.plan_items WHERE type = 'bug' AND repo IN "
        "(SELECT repo FROM git.repos WHERE role = 'clone')"
    ).fetchall()
    total = len(rows)
    inherited = sum(1 for (t,) in rows if t and ("template" in t.lower() or "inherit" in t.lower()))
    return [{"clone_bug_items": total, "mentioning_template_or_inheritance": inherited,
             "note": "proxy via title text, not a confirmed origin trace"}]


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
