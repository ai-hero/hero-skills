"""Q10.xx / RQ-h6-049 -- How many turns and PRs does a goal take to
complete, given that goals have no stated budget?
Proxy: goal-linked items' merged PR count (via commits.pr_number for
commits on items with that goal_id) -- turns aren't linked to a specific
goal anywhere, so only the PR side is answerable.
"""
RQ_ID = "RQ-h6-049"
QUESTION = "How many PRs does a goal take to complete?"

SQL = """
SELECT g.repo, g.goal_id, COUNT(DISTINCT c.pr_number) AS prs
FROM plans.goals g
JOIN plans.plan_items i ON i.repo = g.repo AND i.goal_id = g.goal_id
JOIN git.commits c ON c.repo = i.repo AND c.plan_item_ref = i.item_id AND c.pr_number IS NOT NULL
GROUP BY g.repo, g.goal_id
"""


def answer(con):
    rows = con.execute(SQL).fetchall()
    if not rows:
        return [{"note": "no goal-to-PR chain resolved -- see NEW-A-01 for why this join is low-coverage"}]
    prs = sorted(r["prs"] for r in rows)
    n = len(prs)
    return [{"goals_matched": n, "median_prs_per_goal": prs[n // 2], "max_prs_for_one_goal": prs[-1]}]


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
