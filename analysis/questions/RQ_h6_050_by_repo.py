"""Q16.xx-style follow-up to RQ-h6-050 -- agent spend per repo, from D9's
session_spend (detectors.sqlite). Multi-branch sessions split their cost
evenly across the branches they touched (see detectors/d9_spend.py); that
under/over-attributes a session that did most of its work on one branch and
touched a second only briefly, so branch_count is reported alongside so a
reader can see how much of a repo's total rode on ambiguous sessions.
"""
RQ_ID = "RQ-h6-050-by-repo"
QUESTION = "How does agent spend split across repos, and how much of that rides on ambiguous multi-branch sessions?"

SQL = """
SELECT repo,
       ROUND(SUM(cost_usd), 2) AS spend,
       COUNT(DISTINCT session_id_hash) AS sessions,
       ROUND(SUM(CASE WHEN branch_count > 1 THEN cost_usd ELSE 0 END), 2) AS spend_from_multi_branch_sessions
FROM detectors.session_spend
GROUP BY repo
ORDER BY spend DESC
"""


def answer(con):
    return con.execute(SQL).fetchall()


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(dict(row))
