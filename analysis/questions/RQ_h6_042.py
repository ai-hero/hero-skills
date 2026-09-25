"""Q10.xx / RQ-h6-042 -- How many agent sessions does one work item take?
D9-backed (detectors.session_spend's item_id column) -- only sessions with
a clean item match count (see RQ-h7-020), so this is a count over that
possibly unrepresentative sample, not a fleet-wide rate.
"""
RQ_ID = "RQ-h6-042"
QUESTION = "How many agent sessions does one work item take?"


def answer(con):
    rows = con.execute(
        "SELECT item_id, COUNT(DISTINCT session_id_hash) AS sessions FROM detectors.session_spend "
        "WHERE item_id IS NOT NULL GROUP BY item_id"
    ).fetchall()
    if not rows:
        return [{"note": "no items with a clean session match"}]
    counts = sorted(r["sessions"] for r in rows)
    n = len(counts)
    return [{"items_matched": n, "median_sessions_per_item": counts[n // 2], "max_sessions_for_one_item": counts[-1],
             "note": "low-coverage sample, see RQ-h7-020"}]


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
