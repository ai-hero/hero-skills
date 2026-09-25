"""Q16.xx / RQ-h2-015 -- From the moment work is authorized to the moment
its PR opens, how much wall time and spend does it take? Proxy: item
ready_ts (the "go" authorization moment) to the PR's created_ts on that
item's linked branch -- weak linkage (via commits.plan_item_ref), reports
the item-to-PR lag it can find.
"""
RQ_ID = "RQ-h2-015"
QUESTION = "From the moment work is authorized to the moment its PR opens, how much wall time does it take?"


def answer(con):
    rows = con.execute(
        "SELECT i.repo, i.ready_ts, p.created_ts FROM plans.plan_items i "
        "JOIN git.commits c ON c.repo = i.repo AND c.plan_item_ref = i.item_id "
        "JOIN github.prs p ON p.repo = c.repo AND p.number = c.pr_number "
        "WHERE i.ready_ts IS NOT NULL AND p.created_ts > i.ready_ts"
    ).fetchall()
    if not rows:
        return [{"note": "no ready_ts-to-PR-open chain resolved -- weak plan_item_ref linkage, see NEW-A-01"}]
    import datetime as dt
    hours = sorted((dt.datetime.fromisoformat(r["created_ts"]) - dt.datetime.fromisoformat(r["ready_ts"])).total_seconds() / 3600
                   for r in rows)
    n = len(hours)
    return [{"matched_item_to_pr_pairs": n, "median_hours_ready_to_pr_open": round(hours[n // 2], 1)}]


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
