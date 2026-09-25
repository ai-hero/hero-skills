"""Q16.xx / RQ-h2-009 -- What share of spend goes to features, bug fixes,
security and compliance work? D9-backed via item type, same join as
RQ-h5-010 but broken out by every type, not just security.
"""
RQ_ID = "RQ-h2-009"
QUESTION = "What share of spend goes to features, bug fixes, security and compliance work?"


def answer(con):
    rows = con.execute(
        "SELECT s.cost_usd, i.type FROM detectors.session_spend s "
        "JOIN plans.plan_items i ON i.repo = s.repo AND i.item_id = s.item_id WHERE s.item_id IS NOT NULL"
    ).fetchall()
    if not rows:
        return [{"note": "no item-matched spend rows -- see RQ-h7-020 for D9's coverage caveat"}]
    by_type = {}
    for r in rows:
        by_type[r["type"]] = by_type.get(r["type"], 0) + r["cost_usd"]
    total = sum(by_type.values())
    return [{"type": t, "spend": round(v, 2), "share": round(v / total, 3)} for t, v in
            sorted(by_type.items(), key=lambda kv: -kv[1])] + \
           [{"note": "low-coverage sample, see RQ-h7-020"}]


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
