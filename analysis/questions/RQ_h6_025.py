"""Q10.xx / RQ-h6-025 -- How long does a bug introduced by a process-plugin
change take to fix, and does that time change over the study? Same D3+D5
candidate-regression chain as NEW-C10-03, reporting the lag distribution
here instead of just the count.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ingest.fleet import PLUGIN_REPO_NAME

RQ_ID = "RQ-h6-025"
QUESTION = "How long does a bug introduced by a process-plugin change take to fix?"

SQL = """
SELECT p.downstream_repo, p.downstream_sha, c.pr_number, p.upstream_sha
FROM detectors.propagation p
LEFT JOIN git.commits c ON c.repo = p.downstream_repo AND c.sha = p.downstream_sha
WHERE p.upstream_repo = ? AND c.pr_number IS NOT NULL
"""


def answer(con):
    rows = con.execute(SQL, (PLUGIN_REPO_NAME,)).fetchall()
    lags = []
    for r in rows:
        f = con.execute(
            "SELECT followup_within_14d_days FROM detectors.followups WHERE repo = ? AND number = ?",
            (r["downstream_repo"], r["pr_number"]),
        ).fetchone()
        if f and f[0] is not None:
            lags.append(f[0])
    if not lags:
        return [{"note": "no candidate regressions with a measurable fix lag in this window"}]
    lags.sort()
    n = len(lags)
    return [{
        "candidate_regressions_with_a_fix": n,
        "median_days_to_fix": lags[n // 2],
        "max_days_to_fix": lags[-1],
        "note": "upper bound via D5's same-file-touched-within-14d heuristic, not confirmed bug/fix pairs",
    }]


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
