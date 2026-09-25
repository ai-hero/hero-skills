"""Q14.xx / RQ-h5-035 -- Does CI-configuration change track a stated cost
constraint such as billed Actions minutes? Proxy: commits touching
.github/workflows whose subject/body mentions cost/minutes/spend/cache
(a cost-motivated CI change), by month.
"""
import re

RQ_ID = "RQ-h5-035"
QUESTION = "Does CI-configuration change track a stated cost constraint such as billed Actions minutes?"

COST_RE = re.compile(r"\b(minutes?|cost|spend|cache|billable)\b", re.I)


def answer(con):
    rows = con.execute(
        "SELECT DISTINCT c.month, c.subject, c.body_redacted FROM git.commit_files cf "
        "JOIN git.commits c ON c.repo = cf.repo AND c.sha = cf.sha "
        "WHERE cf.path LIKE '.github/workflows/%'"
    ).fetchall()
    total = len(rows)
    cost_motivated = sum(1 for r in rows if COST_RE.search(r["subject"] + " " + (r["body_redacted"] or "")))
    return [{"ci_config_commits": total, "cost_motivated_mentions": cost_motivated,
             "cost_motivated_share": round(cost_motivated / total, 3) if total else None}]


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
