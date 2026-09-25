"""Q9.xx / RQ-h1-025 -- For each item category (security, bug, feature),
how long does an item take from creation to done?
"""
RQ_ID = "RQ-h1-025"
QUESTION = "For each item category, how long does an item take from creation to done?"

SQL = "SELECT type, created_ts, done_ts FROM plans.plan_items WHERE type != 'goal' AND created_ts IS NOT NULL AND done_ts IS NOT NULL"


def answer(con):
    import datetime as dt
    rows = con.execute(SQL).fetchall()
    by_type = {}
    for r in rows:
        days = (dt.datetime.fromisoformat(r["done_ts"]) - dt.datetime.fromisoformat(r["created_ts"])).days
        by_type.setdefault(r["type"], []).append(days)
    out = []
    for t, days in sorted(by_type.items()):
        days.sort()
        n = len(days)
        out.append({"type": t, "items": n, "median_days": days[n // 2], "p90_days": days[int(n * 0.9)]})
    return out


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
