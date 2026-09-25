"""Q12.xx / RQ-h1-007 -- What does each app's design record contain:
architecture, UI and tokens, data model? doc_versions.sections/decisions
counts per repo as the size proxy; section NAMES aren't captured, so
"contains X specifically" isn't answerable, only "how much."
"""
RQ_ID = "RQ-h1-007"
QUESTION = "What does each app's design record contain, by size?"


def answer(con):
    rows = con.execute(
        "SELECT repo, sections, decisions, bytes FROM knowledge.doc_versions d WHERE doc = 'DESIGN.md' "
        "AND ts = (SELECT MAX(ts) FROM knowledge.doc_versions d2 WHERE d2.repo = d.repo AND d2.doc = 'DESIGN.md')"
    ).fetchall()
    return [dict(r) for r in rows]


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
