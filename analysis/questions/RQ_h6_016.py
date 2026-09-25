"""Q10.xx / RQ-h6-016 -- What share of goals originates from an automated
audit rather than from human product planning?
plan_items.origin on type='goal' rows: 'wayfare'/'wayfare-sync-plan' read as
automated (a skill created it), 'rahul' as human.
"""
RQ_ID = "RQ-h6-016"
QUESTION = "What share of goals originates from an automated audit rather than from human product planning?"

AUTOMATED_ORIGINS = ("wayfare", "wayfare-sync-plan", "wayfare-grill-idea", "wayfare-run-task", "wayfare-build-task")


def answer(con):
    rows = con.execute("SELECT origin, COUNT(*) AS n FROM plans.plan_items WHERE type = 'goal' GROUP BY origin").fetchall()
    total = sum(r["n"] for r in rows)
    automated = sum(r["n"] for r in rows if r["origin"] in AUTOMATED_ORIGINS)
    return [dict(r) for r in rows] + [{
        "total_goals": total, "automated_origin": automated,
        "automated_share": round(automated / total, 3) if total else None,
    }]


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
