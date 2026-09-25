"""Q13.xx / RQ-h4-009 -- When the template or a shared service ships a
change that breaks consumers, how is it caught: CI, review, or a later
bug report? Combines D3 arrival with D8's CI-catch and RQ-h7-013's human-
review signals on the same downstream PRs.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ingest.fleet import TEMPLATE_REPO, ROLE_OVERRIDES

RQ_ID = "RQ-h4-009"
QUESTION = "When the template or a shared service ships a breaking change, how is it caught: CI, review, or a later bug report?"


def answer(con):
    shared_service = next((r for r, role in ROLE_OVERRIDES.items() if role == "shared service"), None)
    upstreams = [r for r in (TEMPLATE_REPO, shared_service) if r]
    if not upstreams:
        return [{"note": "no template or shared-service repo identified for this fleet"}]
    rows = con.execute(
        f"SELECT p.downstream_repo, c.pr_number FROM detectors.propagation p "
        f"JOIN git.commits c ON c.repo = p.downstream_repo AND c.sha = p.downstream_sha "
        f"WHERE p.upstream_repo IN ({','.join('?' * len(upstreams))}) AND c.pr_number IS NOT NULL", upstreams
    ).fetchall()
    ci_caught = human_reviewed = neither = 0
    for r in rows:
        ci = con.execute(
            "SELECT 1 FROM detectors.gate_firings WHERE gate_kind = 'ci' AND repo = ? LIMIT 1",
            (r["downstream_repo"],),
        ).fetchone()
        human = con.execute(
            "SELECT 1 FROM github.pr_reviews WHERE repo = ? AND number = ? AND reviewer_is_bot = 0 LIMIT 1",
            (r["downstream_repo"], r["pr_number"]),
        ).fetchone()
        if ci:
            ci_caught += 1
        elif human:
            human_reviewed += 1
        else:
            neither += 1
    return [{"downstream_arrivals_with_a_pr": len(rows), "any_ci_catch_on_record": ci_caught,
             "human_reviewed_no_ci_catch": human_reviewed, "neither": neither}]


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
