"""Q11.xx / RQ-h3-016 -- Of the work an agent discovers but doesn't act on
in the moment, what share of those found items ever get done?
D4-backed: found_work items' current status.
"""
RQ_ID = "RQ-h3-016"
QUESTION = "Of the work an agent discovers but doesn't act on in the moment, what share of found items ever get done?"

SHIPPED = ("done", "delivered")


def answer(con):
    rows = con.execute(
        "SELECT i.status FROM detectors.found_work f "
        "JOIN plans.plan_items i ON i.repo = f.repo AND i.item_id = f.item_id"
    ).fetchall()
    total = len(rows)
    done = sum(1 for r in rows if r["status"] in SHIPPED)
    return [{"found_work_items": total, "eventually_done": done,
             "done_share": round(done / total, 3) if total else None}]


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
