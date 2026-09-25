"""Q7.xx / RQ-h5-020 -- How often does the owner intervene directly in the
work-item store (deleting or editing an item outside the normal flow)?
item_logs.kind='mutation' is the closest recorded signal; an intervention
that was never logged as one is not counted.
"""
RQ_ID = "RQ-h5-020"
QUESTION = "How often does the owner intervene directly in the work-item store?"


def answer(con):
    rows = con.execute("SELECT repo, item_id, ts, text_redacted FROM plans.item_logs WHERE kind = 'mutation'").fetchall()
    return [{"mutation_log_entries": len(rows)}] + [dict(r) for r in rows]


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
