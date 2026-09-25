"""Q3.09 / RQ-h6-056 -- What share of work-item log entries are written by
the owner versus an agent?

Not answerable with current data: plans.item_logs has no actor/author
column (schema: repo, item_id, ts, kind, text_redacted) -- ingest/plans.py
never parses one out of the raw markdown log lines. Implemented as an
explicit stub, not omitted, so the gap shows up in bank/coverage.py instead
of silently reading as "not started." Fix: extend ingest/plans.py to parse
a trailing attribution (if the raw `## Log` lines carry one) into a new
column, then this file becomes a two-line GROUP BY.
"""
RQ_ID = "RQ-h6-056"
QUESTION = "What share of work-item log entries are written by the owner versus an agent?"


def answer(con):
    n = con.execute("SELECT COUNT(*) FROM plans.item_logs").fetchone()[0]
    return [{"answerable": False, "reason": "item_logs has no actor column", "total_log_entries": n}]


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
