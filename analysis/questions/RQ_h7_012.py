"""Q4.xx / RQ-h7-012 -- For infrastructure changes with irreversible blast
radius, is the documented human-gate policy followed, or does it degrade
to a rubber-stamp merge? Proxy: PRs in infrastructure-role repos, human
review share (RQ-h7-013's join) scoped to that role.
"""
RQ_ID = "RQ-h7-012"
QUESTION = "For infrastructure changes, is the documented human-gate policy followed, or a rubber-stamp?"


def answer(con):
    rows = con.execute(
        "SELECT p.repo, p.number, "
        "SUM(CASE WHEN r.reviewer_is_bot = 0 THEN 1 ELSE 0 END) AS human_reviews "
        "FROM github.prs p "
        "JOIN git.repos gr ON gr.repo = p.repo "
        "LEFT JOIN github.pr_reviews r ON r.repo = p.repo AND r.number = p.number "
        "WHERE gr.role = 'infrastructure repo' AND p.merged_ts IS NOT NULL "
        "GROUP BY p.repo, p.number"
    ).fetchall()
    total = len(rows)
    human = sum(1 for r in rows if r["human_reviews"] > 0)
    return [{"merged_infra_prs": total, "with_human_review": human,
             "human_review_share": round(human / total, 3) if total else None}]


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
