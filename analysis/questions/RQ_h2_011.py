"""Q16.xx / RQ-h2-011 -- When a fix to the template repo is deferred, how
many times do other agents repeat the same fix in clones before it lands
upstream? Same D7 "look like separate builds" clusters as RQ-h6-002,
counting cluster size for the ones with no template involvement.
"""
RQ_ID = "RQ-h2-011"
QUESTION = "When a fix to the template is deferred, how many times do clones repeat the same fix independently?"


def answer(con):
    rows = con.execute(
        "SELECT cluster_id, GROUP_CONCAT(DISTINCT repo) AS repos FROM detectors.duplicate_fixes GROUP BY cluster_id"
    ).fetchall()
    import os, sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from ingest.fleet import TEMPLATE_REPO
    sizes = []
    for r in rows:
        repos = r["repos"].split(",")
        if TEMPLATE_REPO not in repos:
            sizes.append(len(repos))
    if not sizes:
        return [{"note": "no template-absent clusters found"}]
    sizes.sort()
    n = len(sizes)
    return [{"template_absent_clusters": n, "median_repos_repeating_independently": sizes[n // 2],
             "max_repos_repeating_independently": sizes[-1]}]


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
