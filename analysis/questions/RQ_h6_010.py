"""Q10.xx / RQ-h6-010 -- What share of upkeep work (dependency bumps and
the like) merges through the automated judge versus a human review?
"Upkeep" = a bot-authored PR (author_is_bot, i.e. dependabot). "Automated
judge" = approved only by a bot reviewer (github-actions, the judge);
"human review" = at least one human reviewer state on it.
"""
RQ_ID = "RQ-h6-010"
QUESTION = "What share of upkeep (dependency-bump) work merges through the automated judge versus a human review?"

SQL = """
SELECT p.repo, p.number,
       SUM(CASE WHEN r.reviewer_is_bot = 0 THEN 1 ELSE 0 END) AS human_reviews,
       SUM(CASE WHEN r.reviewer_is_bot = 1 THEN 1 ELSE 0 END) AS bot_reviews
FROM github.prs p
LEFT JOIN github.pr_reviews r ON r.repo = p.repo AND r.number = p.number
WHERE p.author_is_bot = 1 AND p.merged_ts IS NOT NULL
GROUP BY p.repo, p.number
"""


def answer(con):
    rows = con.execute(SQL).fetchall()
    total = len(rows)
    judge_only = sum(1 for r in rows if r["human_reviews"] == 0 and r["bot_reviews"] > 0)
    human = sum(1 for r in rows if r["human_reviews"] > 0)
    neither = sum(1 for r in rows if r["human_reviews"] == 0 and r["bot_reviews"] == 0)
    return [{
        "merged_bot_authored_prs": total,
        "judge_only": judge_only, "judge_only_share": round(judge_only / total, 3) if total else None,
        "had_human_review": human, "human_share": round(human / total, 3) if total else None,
        "no_review_at_all": neither,
    }]


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
