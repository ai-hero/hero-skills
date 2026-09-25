"""Q9.xx / RQ-h3-003 -- How often does a unit of work's completion
report claim more than was actually done or verified, and how would we
know? sql half: PRs merged with zero review comments and zero CI gate
firings are a rough proxy for "claimed done, nothing checked it" --
not for "claimed more than was true", which needs comparing the PR
body's claims against the actual diff, a genuine semantic-judgment task.
"""
RQ_ID = "RQ-h3-003"
QUESTION = "How often does a completion report claim more than was actually done or verified, and how would we know?"


def answer(con):
    merged = con.execute("SELECT COUNT(*) AS n FROM github.prs WHERE merged_ts IS NOT NULL").fetchone()["n"]
    unchecked = con.execute(
        "SELECT COUNT(*) AS n FROM github.prs p WHERE p.merged_ts IS NOT NULL AND p.review_count = 0 "
        "AND NOT EXISTS (SELECT 1 FROM detectors.gate_firings g WHERE g.repo = p.repo)"
    ).fetchone()["n"]
    return [{"merged_prs": merged, "merged_with_zero_review_and_no_gate_in_repo": unchecked,
             "answerable_by_code": "partial",
             "reason": "the count above is a proxy for merges nothing independently checked, not for "
                       "a claim exceeding the actual work; verifying that needs a Haiku or human "
                       "comparison of each PR body's stated scope against its diff, not built here"}]


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
