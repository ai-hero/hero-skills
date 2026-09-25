"""Q9.xx / RQ-h1-010 -- How often does a work item's scope grow between
planning and completion? Proxy: item_logs entries of kind 'note' or
'mistake' mentioning 'scope' after the item's ready_ts -- a scope-change
discussion happening after planning was supposedly locked in.
"""
RQ_ID = "RQ-h1-010"
QUESTION = "How often does a work item's scope grow between planning and completion?"


def answer(con):
    rows = con.execute(
        "SELECT i.repo, i.item_id, i.ready_ts, l.ts, l.text_redacted FROM plans.plan_items i "
        "JOIN plans.item_logs l ON l.repo = i.repo AND l.item_id = i.item_id "
        "WHERE i.ready_ts IS NOT NULL AND l.ts > i.ready_ts AND l.text_redacted LIKE '%scope%'"
    ).fetchall()
    distinct_items = {(r["repo"], r["item_id"]) for r in rows}
    return [{"post_ready_scope_mentions": len(rows), "distinct_items_affected": len(distinct_items)}]


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
