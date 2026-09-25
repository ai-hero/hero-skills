"""Q14.xx / RQ-h5-006 -- How many violations of an append-only or
stay-in-sync rule for design records has the fleet had? Same
decisions-per-commit signal as RQ-h4-022 (a repo where several decisions
share one commit suggests a bulk rewrite, i.e. a possible append-only
violation), reframed as a fleet-wide count with a threshold.
"""
RQ_ID = "RQ-h5-006"
QUESTION = "How many violations of an append-only or stay-in-sync rule for design records has the fleet had?"


def answer(con):
    from questions.RQ_h4_022 import answer as base_answer
    rows = base_answer(con)
    suspect = [r for r in rows if isinstance(r, dict) and r.get("decisions_per_commit", 0) >= 2]
    return [{"repos_checked": len(rows), "repos_with_bulk_rewrite_pattern": len(suspect)}] + suspect


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
