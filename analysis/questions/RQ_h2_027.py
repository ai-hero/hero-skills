"""Q16.xx / RQ-h2-027 -- How much work-in-progress does the factory carry
(open items and PRs, parallel sessions) at once? Snapshot of current state
plus the peak-concurrency number RQ-h6-019 already computed.
"""
RQ_ID = "RQ-h2-027"
QUESTION = "How much work-in-progress does the factory carry: open items, open PRs, parallel sessions?"


def answer(con):
    open_items = con.execute(
        "SELECT COUNT(*) FROM plans.plan_items WHERE status NOT IN "
        "('done', 'delivered', 'dropped') AND type != 'goal'"
    ).fetchone()[0]
    open_prs = con.execute("SELECT COUNT(*) FROM github.prs WHERE state != 'MERGED' AND merged_ts IS NULL").fetchone()[0]
    from questions.RQ_h6_019 import answer as concurrency_answer
    peak = concurrency_answer(con)[0]
    return [{"open_work_items": open_items, "open_prs": open_prs, **peak}]


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
