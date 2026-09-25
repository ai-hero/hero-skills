"""Q13.xx / RQ-h4-025 -- Do decisions in the design record trace back to
the commits that motivated them? design_decisions.date_in_text against
commits on the same day in the same repo -- a same-day match is a
plausible trace, not a confirmed causal link (no explicit decision<->commit
id reference exists in either table).
"""
RQ_ID = "RQ-h4-025"
QUESTION = "Do decisions in the design record trace back to the commits that motivated them?"

SQL = "SELECT repo, date_in_text FROM knowledge.design_decisions WHERE date_in_text IS NOT NULL"


def answer(con):
    rows = con.execute(SQL).fetchall()
    total = len(rows)
    traceable = 0
    for r in rows:
        n = con.execute(
            "SELECT COUNT(*) FROM git.commits WHERE repo = ? AND day = ?", (r["repo"], r["date_in_text"])
        ).fetchone()[0]
        traceable += n > 0
    return [{"decisions_with_a_date": total, "same_day_commit_exists": traceable,
             "traceable_share": round(traceable / total, 3) if total else None}]


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
