"""Q11.xx / RQ-h3-001 -- When the owner marks a work item ready before the
plan is complete, how often does that lead to rework? Proxy: items with
ready_ts very close to created_ts (same day, i.e. minimal planning time)
against D5-style rework via item_logs kind='mistake' entries after ready_ts.
"""
RQ_ID = "RQ-h3-001"
QUESTION = "When the owner marks an item ready quickly, does that lead to more rework?"


def answer(con):
    rows = con.execute(
        "SELECT repo, item_id, created_ts, ready_ts FROM plans.plan_items "
        "WHERE created_ts IS NOT NULL AND ready_ts IS NOT NULL"
    ).fetchall()
    fast_ready, slow_ready = [], []
    for r in rows:
        same_day = r["created_ts"][:10] == r["ready_ts"][:10]
        mistakes = con.execute(
            "SELECT COUNT(*) FROM plans.item_logs WHERE repo = ? AND item_id = ? AND kind = 'mistake'",
            (r["repo"], r["item_id"]),
        ).fetchone()[0]
        (fast_ready if same_day else slow_ready).append(mistakes)
    def avg(v): return round(sum(v) / len(v), 2) if v else None
    return [{"same_day_ready_items": len(fast_ready), "avg_mistakes_same_day_ready": avg(fast_ready),
             "later_ready_items": len(slow_ready), "avg_mistakes_later_ready": avg(slow_ready)}]


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
