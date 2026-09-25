"""Q9.xx / RQ-h3-029 -- How often is a work item marked done or a goal
closed while its own security acceptance criterion is unmet? sql half:
merged PRs where a security-kind gate exists in the repo but has no
passing firing near the merge time. Matching a specific *acceptance
criterion* to a specific PR needs a human or Haiku read of the item's
own written criteria, not ingested here.
"""
RQ_ID = "RQ-h3-029"
QUESTION = "How often is a work item marked done while its own security acceptance criterion is unmet?"


def answer(con):
    merged = con.execute(
        "SELECT repo, number, merged_ts FROM github.prs WHERE merged_ts IS NOT NULL"
    ).fetchall()
    sec_gate_repos = {r["repo"] for r in con.execute(
        "SELECT DISTINCT repo FROM detectors.gate_firings WHERE gate_kind LIKE '%security%'"
    ).fetchall()}
    at_risk = 0
    for r in merged:
        if r["repo"] not in sec_gate_repos:
            continue
        passed = con.execute(
            "SELECT 1 FROM detectors.gate_firings WHERE repo = ? AND gate_kind LIKE '%security%' "
            "AND verdict = 'pass' AND ts <= ? ORDER BY ts DESC LIMIT 1",
            (r["repo"], r["merged_ts"]),
        ).fetchone()
        if not passed:
            at_risk += 1
    return [{"merged_prs_in_repos_with_a_security_gate":
                 len([r for r in merged if r["repo"] in sec_gate_repos]),
             "merged_with_no_prior_passing_security_gate_firing": at_risk,
             "answerable_by_code": "partial",
             "reason": "the count above only sees repos with a security-kind gate configured, and "
                       "treats 'no passing firing before merge' as the proxy for an unmet criterion; "
                       "the item's own stated acceptance criterion is not read here"}]


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
