"""Q13.xx / RQ-h4-011 -- How many repos pin a shared workflow or
dependency to a moving reference versus a fixed one? Same CI-01 check
("third-party actions pinned to a full commit SHA") as RQ-h3-025 --
read here as "how many repos fail," the moving-reference count.
"""
RQ_ID = "RQ-h4-011"
QUESTION = "How many repos pin a shared workflow or dependency to a moving reference versus a fixed one?"


def answer(con):
    rows = con.execute(
        "SELECT DISTINCT repo, result FROM knowledge.check_results WHERE check_id = 'CI-01'"
    ).fetchall()
    moving = sum(1 for r in rows if r["result"] == "❌")
    fixed = sum(1 for r in rows if r["result"] == "✅")
    return [{"repos_checked": len(rows), "pinned_to_fixed_sha": fixed, "pinned_to_moving_ref": moving}]


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
