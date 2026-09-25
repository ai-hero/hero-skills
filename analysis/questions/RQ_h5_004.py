"""Q14.xx / RQ-h5-004 -- For a hardening gap later closed, how long did it
exist before it was found? Proxy: security-type items' created_ts minus
the repo's first_commit_ts, as a floor on "how long the gap could have
existed before someone filed it" (not the gap's true introduction date,
which isn't tracked).
"""
RQ_ID = "RQ-h5-004"
QUESTION = "For a hardening gap later closed, how long did it exist before it was found?"


def answer(con):
    rows = con.execute(
        "SELECT i.repo, i.created_ts, r.first_commit_ts FROM plans.plan_items i "
        "JOIN git.repos r ON r.repo = i.repo WHERE i.type = 'security' AND i.created_ts IS NOT NULL"
    ).fetchall()
    import datetime as dt
    days = sorted((dt.datetime.fromisoformat(r["created_ts"]) - dt.datetime.fromisoformat(r["first_commit_ts"])).days
                  for r in rows)
    n = len(days)
    if not n:
        return [{"note": "no security items with created_ts"}]
    return [{"security_items": n, "median_days_since_repo_founding": days[n // 2],
             "note": "floor on gap age (time since repo founding), not the gap's true introduction date"}]


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
