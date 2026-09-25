"""Q9.xx / RQ-h1-039 -- How long does onboarding a new customer
environment take end to end, compared with an established one?
Proxy: days from a clone's first commit to its first merged PR, newest
clone (aihero-steadfast) vs the earlier batch.
"""
RQ_ID = "RQ-h1-039"
QUESTION = "How long does onboarding a new customer environment take, compared with an established one?"


def answer(con):
    import datetime as dt
    repos = con.execute("SELECT repo, first_commit_ts FROM git.repos WHERE role = 'clone'").fetchall()
    out = []
    for r in repos:
        first_pr = con.execute(
            "SELECT MIN(merged_ts) FROM github.prs WHERE repo = ? AND merged_ts IS NOT NULL", (r["repo"],)
        ).fetchone()[0]
        if first_pr:
            days = (dt.datetime.fromisoformat(first_pr) - dt.datetime.fromisoformat(r["first_commit_ts"])).days
            out.append({"repo": r["repo"], "days_to_first_merged_pr": days})
    return sorted(out, key=lambda x: x["days_to_first_merged_pr"])


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
