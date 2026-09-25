"""Q7.xx / RQ-h5-022 -- Does a clone's code size grow with the number of
feature work items tracked against it?
"""
RQ_ID = "RQ-h5-022"
QUESTION = "Does a clone's code size grow with the number of feature work items tracked against it?"

SQL = """
SELECT r.repo,
       (SELECT SUM(insertions) - SUM(deletions) FROM git.commits c WHERE c.repo = r.repo) AS net_lines,
       (SELECT COUNT(*) FROM plans.plan_items i WHERE i.repo = r.repo AND i.type = 'feature') AS feature_items
FROM git.repos r
WHERE r.role = 'clone'
ORDER BY feature_items DESC
"""


def answer(con):
    rows = con.execute(SQL).fetchall()
    return [dict(r, lines_per_feature=round(r["net_lines"] / r["feature_items"], 0) if r["feature_items"] else None)
            for r in rows]


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
