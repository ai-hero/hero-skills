"""Q13.xx / RQ-h4-006 -- How often is a repo's design record checked
against its code, and how much drift accumulates between checks?
Proxy: RQ-h4-025's same-day-commit-exists rate as "checked against code
when written," and doc_versions update frequency as the check cadence.
"""
RQ_ID = "RQ-h4-006"
QUESTION = "How often is a repo's design record checked against its code, and how much drift accumulates between checks?"


def answer(con):
    rows = con.execute(
        "SELECT repo, COUNT(*) AS design_md_commits FROM knowledge.doc_versions WHERE doc = 'DESIGN.md' "
        "GROUP BY repo ORDER BY design_md_commits DESC"
    ).fetchall()
    return [dict(r) for r in rows]


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
