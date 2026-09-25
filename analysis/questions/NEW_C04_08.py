"""Q3.xx / NEW-C04-08 -- Is agent spend recorded per session, with the
model and the branch it ran on? sessions carries cost_usd, main_model,
git_branches together; reports non-null coverage of each.
"""
RQ_ID = "NEW-C04-08"
QUESTION = "Is agent spend recorded per session, with the model and the branch it ran on?"


def answer(con):
    row = con.execute(
        "SELECT COUNT(*) AS n, "
        "SUM(CASE WHEN cost_usd IS NOT NULL THEN 1 ELSE 0 END) AS with_cost, "
        "SUM(CASE WHEN main_model IS NOT NULL THEN 1 ELSE 0 END) AS with_model, "
        "SUM(CASE WHEN git_branches IS NOT NULL THEN 1 ELSE 0 END) AS with_branch "
        "FROM harness.sessions"
    ).fetchone()
    return [dict(row)]


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
