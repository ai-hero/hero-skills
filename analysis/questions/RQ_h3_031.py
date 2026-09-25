"""Q11.xx / RQ-h3-031 -- From discovery to merged fix, how long does a
security finding take, and how many are still open?
plan_items.type='security': created_ts to done_ts for shipped ones; open
count from status not in the shipped set.
"""
RQ_ID = "RQ-h3-031"
QUESTION = "From discovery to merged fix, how long does a security finding take, and how many are still open?"

SHIPPED = ("done", "delivered")


def answer(con):
    import datetime as dt
    rows = con.execute("SELECT status, created_ts, done_ts FROM plans.plan_items WHERE type = 'security'").fetchall()
    lags = []
    open_count = 0
    for r in rows:
        if r["status"] in SHIPPED and r["created_ts"] and r["done_ts"]:
            lags.append((dt.datetime.fromisoformat(r["done_ts"]) - dt.datetime.fromisoformat(r["created_ts"])).days)
        elif r["status"] not in SHIPPED:
            open_count += 1
    lags.sort()
    n = len(lags)
    out = {"security_items": len(rows), "still_open": open_count}
    if n:
        out.update({"fixed_with_dates": n, "median_days_to_fix": lags[n // 2], "p90_days_to_fix": lags[int(n * 0.9)]})
    return [out]


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
