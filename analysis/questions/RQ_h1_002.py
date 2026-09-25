"""Q9.xx / RQ-h1-002 -- At any point in time, what share of each app's
planned customer-facing features is done versus still in flight?
Snapshot as of now: status counted per repo, type='feature' only.
"""
RQ_ID = "RQ-h1-002"
QUESTION = "What share of each app's planned customer-facing features is done versus still in flight?"

DONE_STATUSES = ("done", "delivered")

SQL = "SELECT repo, status, COUNT(*) AS n FROM plans.plan_items WHERE type = 'feature' GROUP BY repo, status"


def answer(con):
    rows = con.execute(SQL).fetchall()
    by_repo = {}
    for r in rows:
        b = by_repo.setdefault(r["repo"], {"done": 0, "in_flight": 0})
        b["done" if r["status"] in DONE_STATUSES else "in_flight"] += r["n"]
    return [{"repo": repo, **v, "total": v["done"] + v["in_flight"],
             "done_share": round(v["done"] / (v["done"] + v["in_flight"]), 3)}
            for repo, v in sorted(by_repo.items())]


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
