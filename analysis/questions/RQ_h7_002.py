"""Q4.xx / RQ-h7-002 -- How many work items does the owner mark ready in
one sitting, and how long do items wait for that mark?
"One sitting" = same repo, same calendar day of ready_ts. Wait time =
ready_ts - created_ts (items missing either timestamp are excluded, not
counted as zero).
"""
RQ_ID = "RQ-h7-002"
QUESTION = "How many work items get marked ready in one sitting, and how long do they wait for it?"

SQL = """
SELECT repo, substr(ready_ts, 1, 10) AS ready_day, COUNT(*) AS items_readied,
       AVG(julianday(ready_ts) - julianday(created_ts)) AS avg_wait_days
FROM plans.plan_items
WHERE ready_ts IS NOT NULL AND created_ts IS NOT NULL
GROUP BY repo, ready_day
ORDER BY items_readied DESC
"""


def answer(con):
    rows = con.execute(SQL).fetchall()
    batch_sizes = [r["items_readied"] for r in rows]
    n = len(batch_sizes)
    summary = {"ready_batches": n,
                "avg_items_per_batch": round(sum(batch_sizes) / n, 2) if n else None,
                "max_items_in_one_sitting": max(batch_sizes) if batch_sizes else None}
    return [summary] + [dict(r, avg_wait_days=round(r["avg_wait_days"], 2)) for r in rows[:20]]


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
