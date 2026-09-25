"""Q14.xx / RQ-h5-037 -- Does the work-item store record actual spend per
item, or only a planned budget?

Reads raw_frontmatter_json for a `budget`/`budget_max` key and for an
actual-cost/spend key (a text search for "spend" also matches item
titles/prose, so only frontmatter keys count). D9's item attribution
(RQ-h7-020) is a separate, harder problem -- this question is just "does
the schema have the field at all."
"""
RQ_ID = "RQ-h5-037"
QUESTION = "Does the work-item store record actual spend per item, or only a planned budget?"

BUDGET_KEYS = ("budget", "budget_max")
COST_KEYS = ("actual_cost", "spend", "cost_usd", "spent")


def answer(con):
    rows = con.execute("SELECT raw_frontmatter_json FROM plans.plan_items").fetchall()
    total = len(rows)
    with_budget = with_cost = 0
    import json
    for (raw,) in rows:
        try:
            d = json.loads(raw) if raw else {}
        except (json.JSONDecodeError, TypeError):
            d = {}
        if any(k in d for k in BUDGET_KEYS):
            with_budget += 1
        if any(k in d for k in COST_KEYS):
            with_cost += 1
    return [{
        "total_items": total,
        "items_with_planned_budget_field": with_budget,
        "items_with_actual_cost_field": with_cost,
        "records_actual_spend": with_cost > 0,
    }]


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
