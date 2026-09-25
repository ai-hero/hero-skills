"""Q14.xx / NEW-C08-H -- Do clones with more compliance work items have
fewer open violations, or resolve them faster?
"""
RQ_ID = "NEW-C08-H"
QUESTION = "Do clones with more compliance work items have fewer open violations?"


def answer(con):
    compliance_items = con.execute(
        "SELECT repo, COUNT(*) AS n FROM plans.plan_items WHERE type = 'security' GROUP BY repo"
    ).fetchall()
    open_violations = con.execute(
        "SELECT repo, COUNT(*) AS n FROM knowledge.check_results WHERE result = '❌' GROUP BY repo"
    ).fetchall()
    items_by_repo = {r["repo"]: r["n"] for r in compliance_items}
    violations_by_repo = {r["repo"]: r["n"] for r in open_violations}
    out = []
    for repo in set(items_by_repo) | set(violations_by_repo):
        out.append({"repo": repo, "compliance_items": items_by_repo.get(repo, 0),
                    "open_violations": violations_by_repo.get(repo, 0)})
    return sorted(out, key=lambda x: -x["compliance_items"])


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
