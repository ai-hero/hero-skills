"""Q4.xx / RQ-h7-001 -- How well does a single status-flip field serve as
a proxy for human review effort, and what does it miss? Proxy: for items
that reach 'ready', how many also carry a decision/mistake log entry near
that transition (review-shaped activity beyond the status field alone).
"""
RQ_ID = "RQ-h7-001"
QUESTION = "How well does a single status-flip field serve as a proxy for human review effort?"


def answer(con):
    ready_items = con.execute(
        "SELECT repo, item_id, ready_ts FROM plans.plan_items WHERE ready_ts IS NOT NULL"
    ).fetchall()
    total = len(ready_items)
    with_log_activity = 0
    for r in ready_items:
        n = con.execute(
            "SELECT COUNT(*) FROM plans.item_logs WHERE repo = ? AND item_id = ? AND kind IN ('decision', 'note')",
            (r["repo"], r["item_id"]),
        ).fetchone()[0]
        with_log_activity += n > 0
    return [{"items_marked_ready": total, "with_additional_log_activity": with_log_activity,
             "share_where_the_flip_alone_undersells_the_effort": round(with_log_activity / total, 3) if total else None}]


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
