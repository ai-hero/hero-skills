"""Q9.xx / RQ-h1-020 -- What is the lead time from a work item's creation
to its completion, and how does it split into legs (created->ready->done)?
Uses plan_items' own lifecycle timestamps directly rather than D6 session
segments -- an item's lead time is the item-level clock; D6 is for what a
SESSION's own elapsed time was spent on (see RQ-h7-003).
"""
RQ_ID = "RQ-h1-020"
QUESTION = "What is the lead time from a work item's creation to completion, and how does it split into legs?"

SQL = """
SELECT repo, created_ts, ready_ts, done_ts
FROM plans.plan_items
WHERE type != 'goal' AND created_ts IS NOT NULL AND done_ts IS NOT NULL
"""


def answer(con):
    import datetime as dt
    rows = con.execute(SQL).fetchall()
    total_days, ready_days = [], []
    for r in rows:
        created = dt.datetime.fromisoformat(r["created_ts"])
        done = dt.datetime.fromisoformat(r["done_ts"])
        total_days.append((done - created).days)
        if r["ready_ts"]:
            ready = dt.datetime.fromisoformat(r["ready_ts"])
            ready_days.append((ready - created).days)
    total_days.sort()
    n = len(total_days)
    out = [{"items_with_full_lifecycle": n,
            "median_total_lead_days": total_days[n // 2] if n else None,
            "p90_total_lead_days": total_days[int(n * 0.9)] if n else None}]
    if ready_days:
        ready_days.sort()
        m = len(ready_days)
        out.append({"items_with_ready_ts": m, "median_created_to_ready_days": ready_days[m // 2]})
    return out


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
