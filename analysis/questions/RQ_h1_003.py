"""Q9.xx / RQ-h1-003 -- How fast is new feature work added per repo each
week, and how does the mix of work shift?
"""
RQ_ID = "RQ-h1-003"
QUESTION = "How fast is new feature work added per repo each week, and how does the mix of work shift?"

SQL = """
SELECT repo, week, type, COUNT(*) AS n
FROM plans.plan_items
WHERE type != 'goal' AND week IS NOT NULL
GROUP BY repo, week, type
"""


def answer(con):
    rows = con.execute(SQL).fetchall()
    by_week = {}
    for r in rows:
        b = by_week.setdefault(r["week"], {})
        b[r["type"]] = b.get(r["type"], 0) + r["n"]
    out = []
    for week, types in sorted(by_week.items()):
        total = sum(types.values())
        out.append({"week": week, "total": total, "feature": types.get("feature", 0),
                    "feature_share": round(types.get("feature", 0) / total, 3)})
    return out


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
