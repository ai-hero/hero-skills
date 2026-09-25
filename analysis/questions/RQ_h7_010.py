"""Q4.xx / RQ-h7-010 -- What share of work-item log entries name the owner
versus an automated actor, by kind of work?

Same gap as RQ-h6-056 (no actor column on item_logs), sliced further by
`kind` here -- still not answerable, so both dimensions are reported as
missing rather than only the coarse one.
"""
RQ_ID = "RQ-h7-010"
QUESTION = "What share of work-item log entries name the owner vs an automated actor, by kind of work?"


def answer(con):
    rows = con.execute("SELECT kind, COUNT(*) FROM plans.item_logs GROUP BY kind ORDER BY 2 DESC").fetchall()
    return [{"answerable": False, "reason": "item_logs has no actor column (see RQ-h6-056)"}] + \
           [{"kind": k, "entries": n} for k, n in rows]


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
