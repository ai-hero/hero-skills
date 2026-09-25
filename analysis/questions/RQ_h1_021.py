"""Q9.xx / RQ-h1-021 -- How long do work items sit ready but not started,
or blocked, and how much of that is a real block versus the queue?
Proxy: ready_ts to done_ts gap (can't separate "blocked" from "queued" --
plan_items has no blocked-on-what field, only status text).
"""
RQ_ID = "RQ-h1-021"
QUESTION = "How long do work items sit ready but not started, or blocked?"

SQL = "SELECT ready_ts, done_ts FROM plans.plan_items WHERE type != 'goal' AND ready_ts IS NOT NULL AND done_ts IS NOT NULL"


def answer(con):
    import datetime as dt
    rows = con.execute(SQL).fetchall()
    days = sorted((dt.datetime.fromisoformat(r["done_ts"]) - dt.datetime.fromisoformat(r["ready_ts"])).days
                  for r in rows)
    n = len(days)
    if not n:
        return [{"note": "no items with both ready_ts and done_ts"}]
    return [{
        "items": n, "median_ready_to_done_days": days[n // 2], "p90_ready_to_done_days": days[int(n * 0.9)],
        "note": "can't distinguish blocked from simply queued -- no block-reason field in the store",
    }]


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
