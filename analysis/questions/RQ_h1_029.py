"""Q6.xx / RQ-h1-029 -- What share of resolved work items were abandoned
without shipping, and what reasons do they give? sql half: PRs closed
without merge, as a proxy for "resolved but not shipped." The reason
each was abandoned needs a Haiku read of the closing comment/PR body,
not built here.
"""
RQ_ID = "RQ-h1-029"
QUESTION = "What share of resolved work items were abandoned without shipping, and what reasons do they give?"


def answer(con):
    total_closed = con.execute(
        "SELECT COUNT(*) AS n FROM github.prs WHERE state = 'closed'"
    ).fetchone()["n"]
    merged = con.execute(
        "SELECT COUNT(*) AS n FROM github.prs WHERE merged_ts IS NOT NULL"
    ).fetchone()["n"]
    closed_unmerged = con.execute(
        "SELECT COUNT(*) AS n FROM github.prs WHERE state = 'closed' AND merged_ts IS NULL"
    ).fetchone()["n"]
    return [{"closed_prs": total_closed, "merged_prs": merged,
             "closed_without_merge_proxy_for_abandoned": closed_unmerged,
             "abandoned_share_of_closed": round(closed_unmerged / total_closed, 4) if total_closed else None},
            {"answerable_by_code": "partial",
             "reason": "PR-level abandonment rate is computable above; this misses work abandoned "
                       "before a PR was ever opened, and the stated reasons for abandonment need a "
                       "Haiku read of each closing comment, not built here"}]


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
