"""Q13.xx / RQ-h4-031 -- Do work items that change architecture reference
the design record's sections or decisions?
Proxy: plan_items whose title suggests architecture work (mentions
"architect"), checked for a DESIGN.md/"design record" mention in that same
title (item_logs body isn't scanned here). plan_items.type has no
"structural" value in this store's vocabulary (feature/chore/bug/goal/
security/feedback/research/polish/unknown/docs) -- title text is the only
available signal.
"""
RQ_ID = "RQ-h4-031"
QUESTION = "Do work items that change architecture reference the design record's sections or decisions?"


def answer(con):
    rows = con.execute(
        "SELECT title FROM plans.plan_items WHERE title LIKE '%architect%'"
    ).fetchall()
    total = len(rows)
    referencing = sum(1 for (t,) in rows if "DESIGN.md" in t or "design record" in t.lower())
    return [{"architecture_shaped_items": total, "titles_mentioning_the_design_record": referencing}]


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
