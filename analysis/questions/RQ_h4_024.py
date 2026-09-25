"""Q13.xx / RQ-h4-024 -- Does every repo's design record still carry the
template's required sections, in name? doc_versions.sections is a count,
not names, so this compares each repo's LATEST section count against the
template's own latest count as the "required" baseline.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ingest.fleet import TEMPLATE_REPO

RQ_ID = "RQ-h4-024"
QUESTION = "Does every repo's design record still carry the template's required sections?"


def answer(con):
    if not TEMPLATE_REPO:
        return [{"note": "no FLEET.md group: template repo in this fleet"}]
    template = con.execute(
        "SELECT sections FROM knowledge.doc_versions WHERE repo = ? AND doc = 'DESIGN.md' ORDER BY ts DESC LIMIT 1",
        (TEMPLATE_REPO,),
    ).fetchone()
    if not template:
        return [{"note": f"no {TEMPLATE_REPO} DESIGN.md snapshot found"}]
    template_sections = template[0]
    rows = con.execute(
        "SELECT repo, sections FROM knowledge.doc_versions d WHERE doc = 'DESIGN.md' AND repo != ? "
        "AND ts = (SELECT MAX(ts) FROM knowledge.doc_versions d2 WHERE d2.repo = d.repo AND d2.doc = 'DESIGN.md')",
        (TEMPLATE_REPO,),
    ).fetchall()
    return [{"template_repo": TEMPLATE_REPO, "template_sections": template_sections}] + \
           [dict(r, at_least_as_many_sections=r["sections"] >= template_sections) for r in rows]


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
