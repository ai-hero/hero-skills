"""Q13.xx / RQ-h4-017 -- Across the fleet's work-item stores, what fraction of
items ship versus are dropped, rejected, or abandoned?

"Shipped" = status done or delivered; "dropped" = status dropped; everything
else is still in flight (todo/planning/ready/committed/active/queued/
reviewing/review) and is reported separately, not folded into either side.
"""
RQ_ID = "RQ-h4-017"
QUESTION = "What fraction of work items ship versus are dropped/abandoned, fleet-wide and per repo?"

SHIPPED = {"done", "delivered"}
DROPPED = {"dropped"}

SQL = "SELECT repo, status, COUNT(*) AS n FROM plans.plan_items WHERE type != 'goal' GROUP BY repo, status"


def _bucket(status):
    if status in SHIPPED:
        return "shipped"
    if status in DROPPED:
        return "dropped"
    return "in_flight"


def answer(con):
    totals = {}
    for repo, status, n in con.execute(SQL).fetchall():
        b = totals.setdefault(repo, {"shipped": 0, "dropped": 0, "in_flight": 0})
        b[_bucket(status)] += n
    out = []
    for repo, b in sorted(totals.items()):
        total = sum(b.values())
        out.append({
            "repo": repo, **b, "total": total,
            "shipped_share": round(b["shipped"] / total, 3) if total else None,
            "dropped_share": round(b["dropped"] / total, 3) if total else None,
        })
    return out


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
