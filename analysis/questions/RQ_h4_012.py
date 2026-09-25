"""Q13.xx / RQ-h4-012 -- When a sweep touches many repos at once, does
human review scale with the repo count? Proxy: D7 duplicate clusters
(a same-fix-many-repos sweep) against how many of those repos' PRs got a
human review.
"""
RQ_ID = "RQ-h4-012"
QUESTION = "When a sweep touches many repos at once, does human review scale with the repo count?"


def answer(con):
    clusters = con.execute(
        "SELECT cluster_id, GROUP_CONCAT(DISTINCT repo) AS repos FROM detectors.duplicate_fixes GROUP BY cluster_id"
    ).fetchall()
    out = []
    for c in clusters:
        repos = c["repos"].split(",")
        if len(repos) < 3:
            continue
        reviewed = 0
        for repo in repos:
            row = con.execute(
                "SELECT 1 FROM github.pr_reviews r JOIN github.prs p ON p.repo = r.repo AND p.number = r.number "
                "WHERE r.repo = ? AND r.reviewer_is_bot = 0 LIMIT 1", (repo,)
            ).fetchone()
            reviewed += bool(row)
        out.append({"cluster_id": c["cluster_id"], "repos_in_sweep": len(repos), "repos_with_human_review": reviewed})
    return out[:20]


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
