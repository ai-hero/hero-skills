"""Q14.xx / RQ-h5-010 -- What share of factory spend goes to compliance
and control-register work? D9-backed via item type, same join pattern as
RQ-h7-020 but bucketed by plan_items.type='security' (this store's closest
proxy for "compliance work").
"""
RQ_ID = "RQ-h5-010"
QUESTION = "What share of factory spend goes to compliance and control-register work?"


def answer(con):
    rows = con.execute(
        "SELECT s.cost_usd, i.type FROM detectors.session_spend s "
        "JOIN plans.plan_items i ON i.repo = s.repo AND i.item_id = s.item_id "
        "WHERE s.item_id IS NOT NULL"
    ).fetchall()
    if not rows:
        return [{"note": "no item-matched spend rows -- see RQ-h7-020 for D9's coverage caveat"}]
    total = sum(r["cost_usd"] for r in rows)
    security = sum(r["cost_usd"] for r in rows if r["type"] == "security")
    return [{"item_matched_spend": round(total, 2), "security_type_spend": round(security, 2),
             "security_share": round(security / total, 3) if total else None,
             "note": "low-coverage sample, see RQ-h7-020"}]


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
