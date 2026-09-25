"""Q9.xx / RQ-h1-013 -- How long does it take to go from a new app to its
first successful deploy? First commit vs first ci_runs row whose workflow
mentions "deploy" and concluded success.
"""
RQ_ID = "RQ-h1-013"
QUESTION = "How long does it take to go from a new app to its first successful deploy?"


def answer(con):
    import datetime as dt
    repos = con.execute("SELECT repo, first_commit_ts FROM git.repos WHERE role = 'clone'").fetchall()
    out = []
    for r in repos:
        deploy = con.execute(
            "SELECT MIN(created_ts) FROM github.ci_runs WHERE repo = ? AND workflow_name LIKE '%eploy%' "
            "AND conclusion = 'success'", (r["repo"],)
        ).fetchone()[0]
        if deploy:
            days = (dt.datetime.fromisoformat(deploy) - dt.datetime.fromisoformat(r["first_commit_ts"])).days
            out.append({"repo": r["repo"], "days_to_first_successful_deploy": days})
        else:
            out.append({"repo": r["repo"], "days_to_first_successful_deploy": None})
    return out


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
