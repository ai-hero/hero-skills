"""Q10.xx / RQ-h6-037 -- Is each repo's design record structurally
complete (every expected section present)? Uses doc_versions.sections
(the section count at each repo's latest DESIGN.md snapshot) against the
fleet's own modal count as the "expected" baseline -- there's no separate
list of required section names ingested, so this flags repos far below
the fleet's norm rather than checking named sections.
"""
RQ_ID = "RQ-h6-037"
QUESTION = "Is each repo's design record structurally complete (every expected section present)?"

SQL = """
SELECT repo, sections FROM knowledge.doc_versions d
WHERE doc = 'DESIGN.md' AND ts = (
    SELECT MAX(ts) FROM knowledge.doc_versions d2 WHERE d2.repo = d.repo AND d2.doc = 'DESIGN.md'
)
"""


def answer(con):
    rows = con.execute(SQL).fetchall()
    counts = sorted(r["sections"] for r in rows)
    n = len(counts)
    modal = counts[n // 2] if n else None
    return [{"repo": r["repo"], "sections": r["sections"], "below_fleet_median": r["sections"] < modal}
            for r in rows] + [{"fleet_median_sections": modal}]


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
