"""Q15.xx / RQ-cicd-008 -- How quickly does a pinned CI dependency update
(an action pin, a base image) propagate across the fleet? D3-backed,
scoped to commits touching .github/workflows or a Dockerfile.
"""
RQ_ID = "RQ-cicd-008"
QUESTION = "How quickly does a pinned CI dependency update propagate across the fleet?"


def answer(con):
    rows = con.execute(
        "SELECT p.lag_hours FROM detectors.propagation p "
        "JOIN git.commits c ON c.repo = p.downstream_repo AND c.sha = p.downstream_sha "
        "JOIN git.commit_files cf ON cf.repo = c.repo AND cf.sha = c.sha "
        "WHERE cf.path LIKE '.github/workflows/%' OR cf.path LIKE '%Dockerfile%'"
    ).fetchall()
    lags = sorted(set(r["lag_hours"] for r in rows))
    n = len(lags)
    if not n:
        return [{"note": "no matched propagated CI-dependency commits"}]
    return [{"matched_arrivals": n, "median_lag_hours": lags[n // 2], "max_lag_hours": lags[-1]}]


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
