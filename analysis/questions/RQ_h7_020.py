"""Q2.12 / RQ-h7-020 -- How reliable is attributing spend to a work item,
and where does attribution confidence break down? Wraps D9's own confidence
buckets (detectors/d9_spend.py) rather than re-deriving them.
"""
RQ_ID = "RQ-h7-020"
QUESTION = "How reliable is attributing spend to a work item, and where does confidence break down?"

SQL = """
SELECT attribution_confidence, COUNT(*) AS rows, ROUND(SUM(cost_usd), 2) AS spend
FROM detectors.session_spend
GROUP BY attribution_confidence
ORDER BY spend DESC
"""


def answer(con):
    rows = con.execute(SQL).fetchall()
    total = sum(r["spend"] for r in rows)
    return [dict(r, share_of_spend=round(r["spend"] / total, 3)) for r in rows]


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
