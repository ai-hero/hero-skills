"""Q11.xx / RQ-h3-038 -- Is secret scanning in place in every repo, and
where does it run only as a local hook versus in CI? Same check_results
source as NEW-C06-01 (STRUCT-04/C-SECRETS); the local-vs-CI split isn't in
check_results (it records pass/fail, not enforcement mechanism) -- checked
separately against each repo's .pre-commit-config.yaml presence (D10).
"""
RQ_ID = "RQ-h3-038"
QUESTION = "Is secret scanning in place in every repo, local hook or CI?"


def answer(con):
    results = con.execute(
        "SELECT DISTINCT repo, result FROM knowledge.check_results WHERE check_id = 'STRUCT-04'"
    ).fetchall()
    precommit = {r["repo"]: r["present"] for r in con.execute(
        "SELECT repo, present FROM detectors.presence WHERE snapshot='head' AND artifact='pre_commit_config'"
    ).fetchall()}
    return [dict(r, has_pre_commit_config=precommit.get(r["repo"])) for r in results]


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
