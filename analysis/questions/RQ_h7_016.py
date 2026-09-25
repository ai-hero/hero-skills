"""Q2.06 / RQ-h7-016 -- Does the work-item store have a schema, when did
each repo adopt each version, and which metrics silently exclude repos that
never migrated? plan_items.schema_era ('old'/'new', set by ingest/plans.py
from the frontmatter shape it saw) per repo, with first/last dates.
"""
RQ_ID = "RQ-h7-016"
QUESTION = "Does the work-item store have a schema, when did each repo adopt each version, and who's excluded?"

SQL = """
SELECT repo, schema_era, COUNT(*) AS items, MIN(created_ts) AS earliest, MAX(created_ts) AS latest
FROM plans.plan_items
GROUP BY repo, schema_era
ORDER BY repo, schema_era
"""


def answer(con):
    rows = con.execute(SQL).fetchall()
    never_migrated = [r["repo"] for r in rows if r["schema_era"] == "old"]
    repos_with_new = {r["repo"] for r in rows if r["schema_era"] == "new"}
    stuck_on_old = [r for r in never_migrated if r not in repos_with_new]
    return [dict(r) for r in rows] + [{
        "repos_never_migrated_to_new_schema": stuck_on_old,
        "note": "a metric that reads only new-era fields (shape, budget, ready_marked) "
                "silently excludes these repos' items",
    }]


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
