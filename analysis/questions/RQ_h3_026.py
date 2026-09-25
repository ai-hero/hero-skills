"""Q11.xx / RQ-h3-026 -- What share of a repo's commits are automated
dependency bumps, and how does that vary by repo?
Proxy: commits with a dependabot/renovate trailer or author, OR a
conventional 'chore' type whose subject mentions 'bump'.
"""
RQ_ID = "RQ-h3-026"
QUESTION = "What share of a repo's commits are automated dependency bumps?"

SQL = """
SELECT repo, is_bot,
       CASE WHEN conv_type = 'chore' AND subject LIKE '%bump%' THEN 1 ELSE 0 END AS looks_like_bump
FROM git.commits
"""


def answer(con):
    rows = con.execute(SQL).fetchall()
    totals = {}
    for r in rows:
        t = totals.setdefault(r["repo"], {"commits": 0, "bump_like": 0})
        t["commits"] += 1
        if r["is_bot"] or r["looks_like_bump"]:
            t["bump_like"] += 1
    return [{"repo": repo, **v, "bump_share": round(v["bump_like"] / v["commits"], 3)}
            for repo, v in sorted(totals.items(), key=lambda kv: -kv[1]["bump_like"])]


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
