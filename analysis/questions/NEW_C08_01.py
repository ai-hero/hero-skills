"""Q14.xx / NEW-C08-01 -- What share of controls carry both a priority and
a deadline? Reads controls.raw_json (raw YAML text, despite the column
name -- see analysis/README.md) for `priority:` and `deadline:` keys.
"""
RQ_ID = "NEW-C08-01"
QUESTION = "What share of controls carry both a priority and a deadline?"


def answer(con):
    rows = con.execute("SELECT raw_json FROM knowledge.controls").fetchall()
    with_priority = sum(1 for (raw,) in rows if "priority:" in raw)
    with_deadline = sum(1 for (raw,) in rows if "deadline:" in raw)
    return [{"controls": len(rows), "with_priority_field": with_priority, "with_deadline_field": with_deadline}]


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
