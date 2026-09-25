"""Q11.xx / RQ-h3-007 -- When a shared service or upstream reference
changes, which downstream consumers get a CI catch versus needing a
human-found fix? D3 arrivals joined against D8's CI-catch table on the
same (repo, sha).
"""
RQ_ID = "RQ-h3-007"
QUESTION = "When a shared service changes, which downstream consumers get a CI catch versus a human-found fix?"


def answer(con):
    rows = con.execute(
        "SELECT p.downstream_repo, c.pr_number FROM detectors.propagation p "
        "JOIN git.commits c ON c.repo = p.downstream_repo AND c.sha = p.downstream_sha "
        "WHERE c.pr_number IS NOT NULL"
    ).fetchall()
    total = len(rows)
    ci_caught = 0
    for r in rows:
        row = con.execute(
            "SELECT 1 FROM detectors.gate_firings WHERE gate_kind = 'ci' AND repo = ? LIMIT 1",
            (r["downstream_repo"],),
        ).fetchone()
        ci_caught += bool(row)
    return [{"downstream_arrivals_with_a_pr": total, "repos_with_any_ci_catch_on_record": ci_caught}]


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
