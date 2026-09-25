"""Q9.xx / RQ-h1-026 -- How long is it from a work item's creation to the
owner marking it ready, and how does that compare across repos?
"""
RQ_ID = "RQ-h1-026"
QUESTION = "How long is it from a work item's creation to the owner marking it ready, per repo?"

SQL = "SELECT repo, created_ts, ready_ts FROM plans.plan_items WHERE created_ts IS NOT NULL AND ready_ts IS NOT NULL"


def answer(con):
    import datetime as dt
    rows = con.execute(SQL).fetchall()
    by_repo = {}
    for r in rows:
        days = (dt.datetime.fromisoformat(r["ready_ts"]) - dt.datetime.fromisoformat(r["created_ts"])).days
        by_repo.setdefault(r["repo"], []).append(days)
    out = []
    for repo, days in sorted(by_repo.items()):
        days.sort()
        n = len(days)
        out.append({"repo": repo, "items": n, "median_days_to_ready": days[n // 2]})
    return out


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
