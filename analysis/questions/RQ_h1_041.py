"""Q6.xx / RQ-h1-041 -- Where does each stage begin (one person with an
agent, the same person with skills, a fleet with a template), and how
sensitive are the findings to those boundaries? sql half: the same
timeline data as RQ-h1-011/NEW-A-09 (first commit dates, template
founding). Human half: judging whether the stage boundaries the data
suggests match the owner's own account.
"""
RQ_ID = "RQ-h1-041"
QUESTION = "Where does each stage begin, and how sensitive are findings to those boundaries?"


def answer(con):
    import os, sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from ingest.fleet import TEMPLATE_REPO, BASELINE_CUTOFF
    rows = con.execute("SELECT repo, role, first_commit_ts FROM git.repos ORDER BY first_commit_ts").fetchall()
    return [{"baseline_cutoff_in_use": BASELINE_CUTOFF, "template_repo": TEMPLATE_REPO}] + \
           [dict(r) for r in rows] + \
           [{"answerable_by_code": "partial",
             "reason": "the timeline is computable; whether it matches the owner's own account of stage "
                       "boundaries is a human judgment, not in this file"}]


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
