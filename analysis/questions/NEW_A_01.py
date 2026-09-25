"""Q2.01 / NEW-A-01 -- Can every commit be linked to a PR, every PR to a
work item, and every work item to a goal? (Preflight)

The unit-of-work rollup (lines -> change set -> commit -> PR -> item ->
goal) only works if these links exist. Reports coverage at each hop
honestly rather than assuming full linkage:
  - commit -> PR: commits.pr_number (parsed from the merge-commit message
    or a "(#N)" suffix by ingest/git.py).
  - PR -> item: no direct column anywhere. The only signal is
    commits.plan_item_ref (a bare number, only where a commit cites one) chained through
    pr_number -- the same low-coverage path D9 documents, not a real link.
  - item -> goal: plan_items.goal_id.
"""
RQ_ID = "NEW-A-01"
QUESTION = "Can every commit be linked to a PR, every PR to a work item, and every work item to a goal?"


def answer(con):
    commits = con.execute("SELECT COUNT(*) AS n, SUM(CASE WHEN pr_number IS NOT NULL THEN 1 ELSE 0 END) AS linked "
                           "FROM git.commits").fetchone()
    prs = con.execute("SELECT COUNT(*) AS n FROM github.prs").fetchone()
    commits_with_item = con.execute(
        "SELECT COUNT(*) AS n FROM git.commits WHERE pr_number IS NOT NULL AND plan_item_ref IS NOT NULL"
    ).fetchone()
    items = con.execute("SELECT COUNT(*) AS n, SUM(CASE WHEN goal_id IS NOT NULL THEN 1 ELSE 0 END) AS linked "
                         "FROM plans.plan_items WHERE type != 'goal'").fetchone()

    return [{
        "commit_to_pr": f"{commits['linked']}/{commits['n']} ({round(commits['linked'] / commits['n'], 3)})",
        "pr_to_item_via_plan_item_ref": f"{commits_with_item['n']}/{prs['n']} PRs "
                                         f"({round(commits_with_item['n'] / prs['n'], 3)}) -- weak: chained through "
                                         f"a bare commit-message number, not a real PR<->item column",
        "item_to_goal": f"{items['linked']}/{items['n']} ({round(items['linked'] / items['n'], 3)})",
    }]


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
