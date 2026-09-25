"""Q9.xx / RQ-h1-023 -- What share of a repo's work items are found work
discovered while doing other work? D4-backed (detectors.found_work is the
discovered_from side of item_edges).
"""
RQ_ID = "RQ-h1-023"
QUESTION = "What share of a repo's work items are found work, discovered while doing other work?"

SQL = """
SELECT i.repo,
       COUNT(*) AS items,
       COUNT(f.item_id) AS found_work_items
FROM plans.plan_items i
LEFT JOIN detectors.found_work f ON f.repo = i.repo AND f.item_id = i.item_id
WHERE i.type != 'goal'
GROUP BY i.repo
"""


def answer(con):
    rows = con.execute(SQL).fetchall()
    return [dict(r, found_work_share=round(r["found_work_items"] / r["items"], 3)) for r in rows]


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
