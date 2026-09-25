"""Q3.xx / NEW-C04-06 -- What share of checks run locally (pre-commit,
pre-push) versus only in CI? Proxy: D10 pre_commit_config presence per
repo as "has a local gate at all" against total checks defined in the
register -- can't split individual checks by where they run (no
enforcement-location field on `checks`), only whether a repo has a
pre-commit config file at all.
"""
RQ_ID = "NEW-C04-06"
QUESTION = "What share of checks run locally versus only in CI?"


def answer(con):
    rows = con.execute(
        "SELECT repo, present FROM detectors.presence WHERE snapshot='head' AND artifact='pre_commit_config'"
    ).fetchall()
    with_local = sum(1 for r in rows if r["present"])
    return [{"repos_checked": len(rows), "repos_with_a_pre_commit_config": with_local,
             "note": "no per-check enforcement-location field exists -- this is repo-level "
                     "'has a local gate at all,' not a per-check split"}]


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
