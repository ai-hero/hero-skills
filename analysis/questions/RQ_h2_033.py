"""Q17.xx / RQ-h2-033 -- Of the security issues found, what share were
caught by agent review, by an audit, and by CI?
Proxy: plan_items.type='security' grouped by origin (the same field
RQ-h6-016 uses for goals) -- 'wayfare'-family origin reads as agent/audit-
found, 'rahul' as human-found; CI-caught isn't separable from this without
a per-item discovery-channel field that doesn't exist.
"""
RQ_ID = "RQ-h2-033"
QUESTION = "Of the security issues found, what share were caught by agent review/audit versus the owner?"


def answer(con):
    rows = con.execute(
        "SELECT origin, COUNT(*) AS n FROM plans.plan_items WHERE type = 'security' GROUP BY origin"
    ).fetchall()
    return [dict(r) for r in rows] + [{
        "note": "no discovery-channel field (CI vs review vs audit) exists on plan_items -- "
                "origin only distinguishes agent-initiated from human-initiated",
    }]


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
