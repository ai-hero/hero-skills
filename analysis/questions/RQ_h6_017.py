"""Q10.xx / RQ-h6-017 -- How often does a product goal include maintenance
or hardening items, against the rule that goals should be product-focused?
Child items via plan_items.goal_id.
"""
RQ_ID = "RQ-h6-017"
QUESTION = "How often does a product goal include maintenance or hardening items?"

MAINTENANCE_TYPES = ("chore", "security", "docs")

SQL = """
SELECT g.repo, g.goal_id, g.title,
       SUM(CASE WHEN i.type IN ('chore', 'security', 'docs') THEN 1 ELSE 0 END) AS maintenance_items,
       SUM(CASE WHEN i.type = 'feature' THEN 1 ELSE 0 END) AS feature_items,
       COUNT(i.item_id) AS total_items
FROM plans.goals g
LEFT JOIN plans.plan_items i ON i.repo = g.repo AND i.goal_id = g.goal_id
GROUP BY g.repo, g.goal_id
HAVING total_items > 0
"""


def answer(con):
    rows = con.execute(SQL).fetchall()
    total = len(rows)
    mixed = sum(1 for r in rows if r["maintenance_items"] > 0 and r["feature_items"] > 0)
    return [{
        "goals_with_child_items": total,
        "goals_mixing_maintenance_and_feature_items": mixed,
        "mixed_share": round(mixed / total, 3) if total else None,
    }]


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
