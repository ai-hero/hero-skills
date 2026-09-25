"""Q17.xx / RQ-h2-019 -- When the owner reverses an operational
decision, what extra spend did the original choice and its reversal
together cost? No decision-reversal log is ingested; git's is_revert/
reverts_sha flags a reverted *commit*, which is a narrower and different
thing than an owner reversing an operational decision. Spend around a
revert is shown as the nearest proxy.
"""
RQ_ID = "RQ-h2-019"
QUESTION = "When the owner reverses an operational decision, what extra spend did the original choice and its reversal together cost?"


def answer(con):
    reverts = con.execute(
        "SELECT repo, sha, reverts_sha, committed_ts FROM git.commits WHERE is_revert = 1"
    ).fetchall()
    return [{"commit_level_reverts_found": len(reverts), "sample": [dict(r) for r in reverts[:10]]},
            {"answerable_by_code": False,
             "reason": "is_revert marks a reverted *commit*, not an owner-level operational-decision "
                       "reversal (e.g. switching a whole approach, not just undoing a patch); "
                       "matching a decision to its spend and its reversal's spend needs a human to "
                       "identify the decision boundary first"}]


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
