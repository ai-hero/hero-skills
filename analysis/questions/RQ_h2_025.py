"""Q16.xx / RQ-h2-025 -- What share of opened PRs and work items complete
rather than being abandoned?
"""
RQ_ID = "RQ-h2-025"
QUESTION = "What share of opened PRs and work items complete rather than being abandoned?"


def answer(con):
    prs = con.execute("SELECT state, COUNT(*) AS n FROM github.prs GROUP BY state").fetchall()
    pr_total = sum(r["n"] for r in prs)
    pr_merged = sum(r["n"] for r in prs if r["state"] == "MERGED")
    items = con.execute("SELECT status, COUNT(*) AS n FROM plans.plan_items WHERE type != 'goal' GROUP BY status").fetchall()
    item_total = sum(r["n"] for r in items)
    item_done = sum(r["n"] for r in items if r["status"] in ("done", "delivered"))
    return [{
        "prs_opened": pr_total, "prs_merged": pr_merged, "pr_completion_rate": round(pr_merged / pr_total, 3),
        "items_opened": item_total, "items_done": item_done, "item_completion_rate": round(item_done / item_total, 3),
    }]


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
