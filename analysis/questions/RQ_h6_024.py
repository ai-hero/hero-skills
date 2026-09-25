"""Q10.xx / RQ-h6-024 -- On what date did each core capability of the
process plugin first ship? "Core capability" is a curated list (subagents,
worktrees, auto mode, ...) that no table defines -- skill_versions gives
per-skill first-add dates (see RQ-h6-026's cumulative count), but deciding
which skills count as a "core capability" is an editorial judgment this
file won't make silently. Left as a stub pointing at the raw data a human
would curate from.
"""
RQ_ID = "RQ-h6-024"
QUESTION = "On what date did each core capability of the process plugin first ship?"


def answer(con):
    first_ship = con.execute(
        "SELECT skill, MIN(day) AS first_day FROM knowledge.skill_versions GROUP BY skill ORDER BY first_day"
    ).fetchall()
    return [{"note": "no curated 'core capability' list exists -- here is every skill's own first-ship date, "
                      "for a human to pick from"}] + [dict(r) for r in first_ship]


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
