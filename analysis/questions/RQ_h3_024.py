"""Q11.xx / RQ-h3-024 -- When a dependency gets a security fix, how long
does each repo take to apply it? Proxy: D3 propagation with
match_method='exact_subject' between two repos on commits whose subject
matches a dependency-bump shape (conv_type='chore' + 'bump'), as the
"same fix landed elsewhere" signal; lag_hours is the apply-time proxy.
"""
RQ_ID = "RQ-h3-024"
QUESTION = "When a dependency gets a security fix, how long does each repo take to apply it?"

SQL = """
SELECT p.downstream_repo, p.lag_hours
FROM detectors.propagation p
JOIN git.commits c ON c.repo = p.downstream_repo AND c.sha = p.downstream_sha
WHERE c.conv_type = 'chore' AND c.subject LIKE '%bump%'
"""


def answer(con):
    rows = con.execute(SQL).fetchall()
    if not rows:
        return [{"note": "no propagated dependency-bump-shaped commits found"}]
    by_repo = {}
    for r in rows:
        by_repo.setdefault(r["downstream_repo"], []).append(r["lag_hours"])
    return [{"repo": repo, "matched_bumps": len(lags), "median_lag_hours": sorted(lags)[len(lags) // 2]}
            for repo, lags in by_repo.items()]


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
