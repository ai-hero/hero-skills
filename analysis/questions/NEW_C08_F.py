"""Q14.xx / NEW-C08-F -- How many human gates does a work item pass
through, and has that count changed over time?
Proxy: item_logs.kind='decision' entries per item (the closest recorded
"a human weighed in here" marker) as a floor -- ready-marking itself isn't
a separate log kind, it's the ready_ts field (RQ-h7-002 covers that angle).
"""
RQ_ID = "NEW-C08-F"
QUESTION = "How many human gates does a work item pass through, and has that count changed over time?"


def answer(con):
    rows = con.execute(
        "SELECT substr(ts, 1, 7) AS month, COUNT(*) AS decision_entries "
        "FROM plans.item_logs WHERE kind = 'decision' AND ts IS NOT NULL GROUP BY month ORDER BY month"
    ).fetchall()
    per_item = con.execute(
        "SELECT COUNT(*) AS n FROM plans.item_logs WHERE kind = 'decision'"
    ).fetchone()[0]
    items_with_decision = con.execute(
        "SELECT COUNT(DISTINCT repo || ':' || item_id) FROM plans.item_logs WHERE kind = 'decision'"
    ).fetchone()[0]
    return [{"decision_log_entries": per_item, "distinct_items_with_a_decision_entry": items_with_decision}] + \
           [dict(r) for r in rows]


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
