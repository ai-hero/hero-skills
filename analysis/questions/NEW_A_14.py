"""Q1.xx / NEW-A-14 -- Is creating a new app, and deploying it, automated
end to end or does each step need the owner? sql half: whether each
repo's history shows a CI/deploy gate ever firing at all, as a signal
for automation existing; whether a *human* step is still required in
that path is a methodology judgment on the workflow files themselves.
"""
RQ_ID = "NEW-A-14"
QUESTION = "Is creating a new app, and deploying it, automated end to end or does each step need the owner?"


def answer(con):
    deploy_gates = con.execute(
        "SELECT repo, gate_kind, COUNT(*) AS n FROM detectors.gate_firings "
        "WHERE gate_kind LIKE '%deploy%' OR gate_kind LIKE '%release%' GROUP BY 1, 2"
    ).fetchall()
    return [{"repos_with_a_deploy_or_release_gate": [dict(r) for r in deploy_gates]},
            {"answerable_by_code": "partial",
             "reason": "presence of a deploy/release gate firing is a signal that *some* step is "
                       "automated; confirming the full app-creation-to-deploy path needs no human "
                       "click requires reading the actual workflow files, which is a human check"}]


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
