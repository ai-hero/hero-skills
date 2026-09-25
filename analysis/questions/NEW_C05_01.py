"""Q10.xx / NEW-C05-01 -- Does the factory record agent mistakes anywhere,
in a form a script can count?
"""
RQ_ID = "NEW-C05-01"
QUESTION = "Does the factory record agent mistakes anywhere, in a form a script can count?"

SQL = "SELECT repo, COUNT(*) AS mistake_entries FROM plans.item_logs WHERE kind = 'mistake' GROUP BY repo ORDER BY mistake_entries DESC"


def answer(con):
    rows = con.execute(SQL).fetchall()
    total = sum(r["mistake_entries"] for r in rows)
    return [{"recorded_as_countable": total > 0, "total_mistake_entries": total}] + [dict(r) for r in rows]


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
