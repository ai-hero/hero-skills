"""Q13.xx / NEW-C07-E -- After a multi-repo sweep, how many conflicts or
divergences surfaced afterward? Proxy: D7 clusters (a sweep) where at
least one member commit later got a D5 follow-up fix -- a conflict/
divergence surfacing as a same-file fix after the sweep landed.
"""
RQ_ID = "NEW-C07-E"
QUESTION = "After a multi-repo sweep, how many conflicts or divergences surfaced afterward?"


def answer(con):
    clusters = con.execute(
        "SELECT cluster_id, repo, sha FROM detectors.duplicate_fixes"
    ).fetchall()
    by_cluster = {}
    for r in clusters:
        by_cluster.setdefault(r["cluster_id"], []).append((r["repo"], r["sha"]))
    surfaced = 0
    for cid, members in by_cluster.items():
        for repo, sha in members:
            pr = con.execute("SELECT pr_number FROM git.commits WHERE repo = ? AND sha = ?", (repo, sha)).fetchone()
            if pr and pr[0]:
                f = con.execute(
                    "SELECT followup_within_14d_days FROM detectors.followups WHERE repo = ? AND number = ?",
                    (repo, pr[0]),
                ).fetchone()
                if f and f[0] is not None:
                    surfaced += 1
                    break
    return [{"sweeps": len(by_cluster), "sweeps_with_a_later_followup_fix": surfaced}]


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
