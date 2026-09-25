"""Q11.xx / RQ-h3-009 -- How many work items or hardening findings sit
stale or silently unaddressed before someone notices?
Items still open (not done/delivered/dropped) with no item_logs entry in
the last 30 days of the ingest window.
"""
RQ_ID = "RQ-h3-009"
QUESTION = "How many work items or hardening findings sit stale or silently unaddressed?"

OPEN_STATUSES = ("todo", "planning", "ready", "committed", "active", "queued", "reviewing", "review", "new")


def answer(con):
    latest = con.execute("SELECT MAX(ts) FROM plans.item_logs").fetchone()[0]
    if not latest:
        return [{"note": "no item_logs rows"}]
    items = con.execute(
        f"SELECT repo, item_id, type FROM plans.plan_items WHERE status IN {OPEN_STATUSES}"
    ).fetchall()
    stale = 0
    for r in items:
        last_touch = con.execute(
            "SELECT MAX(ts) FROM plans.item_logs WHERE repo = ? AND item_id = ?", (r["repo"], r["item_id"])
        ).fetchone()[0]
        if not last_touch:
            stale += 1
            continue
        import datetime as dt
        gap = (dt.datetime.fromisoformat(latest) - dt.datetime.fromisoformat(last_touch)).days
        if gap > 30:
            stale += 1
    return [{"open_items": len(items), "no_activity_in_30d_or_ever": stale}]


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
