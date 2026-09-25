"""Q4.xx / RQ-h7-013 -- What share of merged work gets a substantive human
review versus agent-only review?
"Substantive human review" = at least one pr_reviews row with reviewer_is_bot=0
and state in (APPROVED, CHANGES_REQUESTED, COMMENTED) -- a review, not just
a bot check. D8's gate_firings table already has this shape; this slices it
by merged PR instead of raw review-verdict counts.
"""
RQ_ID = "RQ-h7-013"
QUESTION = "What share of merged work gets a substantive human review versus agent-only review?"

SQL = """
SELECT p.repo, p.number,
       SUM(CASE WHEN r.reviewer_is_bot = 0 THEN 1 ELSE 0 END) AS human_reviews
FROM github.prs p
LEFT JOIN github.pr_reviews r ON r.repo = p.repo AND r.number = p.number
WHERE p.merged_ts IS NOT NULL
GROUP BY p.repo, p.number
"""


def answer(con):
    rows = con.execute(SQL).fetchall()
    total = len(rows)
    human = sum(1 for r in rows if r["human_reviews"] > 0)
    return [{"merged_prs": total, "with_human_review": human,
             "human_review_share": round(human / total, 3) if total else None,
             "agent_only_share": round(1 - human / total, 3) if total else None}]


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
