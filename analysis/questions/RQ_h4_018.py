"""Q13.xx / RQ-h4-018 -- When an agent finds new work while doing something
else, how deep and wide do those chains run, per repo? Same D4 source as
RQ-h1-018, broken out per repo.
"""
RQ_ID = "RQ-h4-018"
QUESTION = "When an agent finds new work while doing something else, how deep and wide do those chains run, per repo?"

SQL = "SELECT repo, depth, root_fan_out FROM detectors.found_work"


def answer(con):
    rows = con.execute(SQL).fetchall()
    by_repo = {}
    for r in rows:
        by_repo.setdefault(r["repo"], []).append(r["depth"])
    return [{"repo": repo, "found_work_edges": len(v), "max_depth": max(v)} for repo, v in sorted(by_repo.items())]


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
