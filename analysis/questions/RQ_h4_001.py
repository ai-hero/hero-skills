"""Q13.xx / RQ-h4-001 -- What share of cross-repo messages with a named
destination were actually received (deposited into the target repo's
inbox)? plans.messages.status carries this directly ("new" = drafted but
maybe not deposited, e.g. when the target repo has no inbox yet).
"""
RQ_ID = "RQ-h4-001"
QUESTION = "What share of cross-repo messages with a named destination were actually received?"


def answer(con):
    rows = con.execute("SELECT status, COUNT(*) AS n FROM plans.messages GROUP BY status").fetchall()
    total = sum(r["n"] for r in rows)
    if not total:
        return [{"note": "no messages recorded"}]
    return [dict(r) for r in rows] + [{"total": total}]


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
