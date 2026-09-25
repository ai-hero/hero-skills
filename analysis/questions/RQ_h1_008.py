"""Q12.xx / RQ-h1-008 -- When the template's design record gains a new
required element, how long do existing clones take to catch up? Uses
knowledge.doc_versions.sections growth in the template (a jump in section
count = a new element) matched against each clone's own section-count
history for the next jump after that date.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ingest.fleet import TEMPLATE_REPO

RQ_ID = "RQ-h1-008"
QUESTION = "When the template's design record gains a new required element, how long do clones take to catch up?"


def answer(con):
    if not TEMPLATE_REPO:
        return [{"note": "no FLEET.md group: template repo in this fleet"}]
    rows = con.execute(
        "SELECT ts, sections FROM knowledge.doc_versions WHERE repo = ? AND doc = 'DESIGN.md' ORDER BY ts",
        (TEMPLATE_REPO,),
    ).fetchall()
    jumps = []
    prev = None
    for r in rows:
        if prev is not None and r["sections"] > prev:
            jumps.append(r["ts"])
        prev = r["sections"]
    return [{"template_section_count_increases": len(jumps), "dates": jumps[-10:]}]


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
