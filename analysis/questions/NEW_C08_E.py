"""Q14.xx / NEW-C08-E -- Does a younger clone show more defects per
commit than an older one, at the same maturity point? D5-backed:
followup-fix rate (proxy for "defect found") per repo, against repo age.
"""
RQ_ID = "NEW-C08-E"
QUESTION = "Does a younger clone show more defects per commit than an older one?"


def answer(con):
    import datetime as dt
    ages = {r["repo"]: r["first_commit_ts"] for r in con.execute(
        "SELECT repo, first_commit_ts FROM git.repos WHERE role = 'clone'"
    ).fetchall()}
    repos = list(ages)
    rows = con.execute(
        "SELECT c.repo, COUNT(*) AS commits, "
        "SUM(CASE WHEN f.followup_within_14d_days IS NOT NULL THEN 1 ELSE 0 END) AS followed_up "
        "FROM git.commits c LEFT JOIN detectors.followups f ON f.repo = c.repo AND f.number = c.pr_number "
        f"WHERE c.repo IN ({','.join('?' * len(repos))}) GROUP BY c.repo", repos
    ).fetchall()
    out = []
    for r in rows:
        age_days = (dt.datetime.now(dt.timezone.utc) - dt.datetime.fromisoformat(ages[r["repo"]])).days
        out.append({"repo": r["repo"], "age_days": age_days, "commits": r["commits"],
                    "followup_rate": round(r["followed_up"] / r["commits"], 3) if r["commits"] else None})
    return sorted(out, key=lambda x: x["age_days"])


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
