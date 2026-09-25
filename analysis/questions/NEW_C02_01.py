"""Q9.xx / NEW-C02-01 -- Does each repo have a work-item store with a
defined schema (item types, statuses)? D10-adjacent: plan_items itself is
the evidence (every repo with rows has one), reported with its type/status
vocabulary size per repo as the "defined" signal.
"""
RQ_ID = "NEW-C02-01"
QUESTION = "Does each repo have a work-item store with a defined schema (item types, statuses)?"

SQL = """
SELECT repo, COUNT(*) AS items, COUNT(DISTINCT type) AS distinct_types, COUNT(DISTINCT status) AS distinct_statuses
FROM plans.plan_items
GROUP BY repo
"""


def answer(con):
    return con.execute(SQL).fetchall()


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(dict(row))
