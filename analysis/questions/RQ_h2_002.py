"""Q16.xx / RQ-h2-002 -- What share of CI minutes and PRs goes to
dependency-update bots versus agent-authored feature work?

"Bot" = prs.author_is_bot (dependabot etc, from github.py's login-shape
heuristic). CI minutes are attributed to a PR's own run set via head_branch
matching head_ref -- an approximation: a run on a branch that was force-
pushed or reused loses that link, so this undercounts rather than overcounts.
"""
RQ_ID = "RQ-h2-002"
QUESTION = "What share of CI minutes and PRs goes to dependency bots vs feature work?"

SQL = """
SELECT
    CASE WHEN p.author_is_bot = 1 THEN 'bot' ELSE 'human_or_agent' END AS author_kind,
    COUNT(DISTINCT p.repo || ':' || p.number) AS prs,
    COUNT(DISTINCT c.repo || ':' || c.run_id) AS ci_runs,
    ROUND(SUM(c.duration_s) / 60.0, 1) AS ci_minutes
FROM github.prs p
LEFT JOIN github.ci_runs c ON c.repo = p.repo AND c.head_branch = p.head_ref
GROUP BY author_kind
"""


def answer(con):
    return con.execute(SQL).fetchall()


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(dict(row))
