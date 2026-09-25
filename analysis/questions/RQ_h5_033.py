"""Q14.xx / RQ-h5-033 -- Does the work-item store have a defined schema,
how often has it changed, and how many repos are on an old version?
Two eras exist (old/new, ingest/plans.py's own discovery, not documented
anywhere else) -- "how often changed" is answerable only as "at least
once," since no finer schema-version history is tracked.
"""
RQ_ID = "RQ-h5-033"
QUESTION = "Does the work-item store have a defined schema, how often has it changed, and who's on an old version?"


def answer(con):
    rows = con.execute(
        "SELECT repo, schema_era, COUNT(*) AS n FROM plans.plan_items GROUP BY repo, schema_era"
    ).fetchall()
    by_repo = {}
    for r in rows:
        by_repo.setdefault(r["repo"], set()).add(r["schema_era"])
    only_old = [r for r, eras in by_repo.items() if eras == {"old"}]
    return [{"schema_eras_observed": 2, "repos": len(by_repo), "repos_only_on_old_schema": only_old}]


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
