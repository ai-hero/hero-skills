"""Q19.xx / RQ-h7-045 -- When did the owner's corrections shift from
direction and taste to catching agent errors? d_prompt_kind.py's Haiku
classifier already labels every flagged prompt as correction/redirect/
approval/question/other with a timestamp; a month-by-month trend of
correction/redirect share is the closest sql-computable signal. Whether
a given month's corrections are "taste" vs "error-catching" is a finer
distinction the classifier doesn't make.
"""
RQ_ID = "RQ-h7-045"
QUESTION = "When did the owner's corrections shift from direction and taste to catching agent errors?"


def answer(con):
    rows = con.execute(
        "SELECT strftime('%Y-%m', p.ts) AS month, k.kind, COUNT(*) AS n "
        "FROM detectors.prompt_kind_by_prompt p "
        "JOIN detectors.prompt_kind k ON k.content_hash = p.content_hash "
        "WHERE p.flagged = 1 "
        "GROUP BY 1, 2 ORDER BY 1"
    ).fetchall()
    by_month = {}
    for r in rows:
        by_month.setdefault(r["month"], {})[r["kind"]] = r["n"]
    return [{"month": m, **counts} for m, counts in sorted(by_month.items())] + [
        {"answerable_by_code": "partial",
         "reason": "the month-by-month correction/redirect volume trend is above; distinguishing "
                   "'taste' corrections from 'error-catching' ones within that trend needs a finer "
                   "classifier or a human read of the flagged prompts"}
    ]


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
