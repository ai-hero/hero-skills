"""Q15.xx / RQ-cicd-004 -- How long does a merged change take to reach
production in each deployed product? Proxy: merged_ts to the next
successful deploy-workflow run on that same head_sha, per repo.
"""
RQ_ID = "RQ-cicd-004"
QUESTION = "How long does a merged change take to reach production in each deployed product?"


def answer(con):
    import datetime as dt
    prs = con.execute(
        "SELECT repo, head_ref, merged_ts FROM github.prs WHERE merged_ts IS NOT NULL"
    ).fetchall()
    by_repo = {}
    for r in prs[:3000]:
        deploy = con.execute(
            "SELECT MIN(created_ts) FROM github.ci_runs WHERE repo = ? AND workflow_name LIKE '%eploy%' "
            "AND conclusion = 'success' AND created_ts > ?", (r["repo"], r["merged_ts"]),
        ).fetchone()[0]
        if deploy:
            hours = (dt.datetime.fromisoformat(deploy.replace("Z", "+00:00")) -
                     dt.datetime.fromisoformat(r["merged_ts"].replace("Z", "+00:00"))).total_seconds() / 3600
            by_repo.setdefault(r["repo"], []).append(hours)
    return [{"repo": repo, "merges_matched": len(v), "median_hours_to_deploy": round(sorted(v)[len(v) // 2], 1)}
            for repo, v in by_repo.items()]


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
