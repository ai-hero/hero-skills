"""Q13.xx / RQ-h4-008 -- When a design source flags a divergence from
the code, what share end in a code-verified fix, a duplicate, or a
stall? sql half: D2's drifted-now flag gives current divergences; how
each one is eventually resolved (fix/duplicate/stall) needs reading the
follow-up commit or issue, which is a Haiku-scale text-judgment task
this repo hasn't built a classifier for.
"""
RQ_ID = "RQ-h4-008"
QUESTION = "When a design source flags a divergence from the code, what share end in a code-verified fix, a duplicate, or a stall?"


def answer(con):
    rows = con.execute(
        "SELECT artifact, repo, drifted_now, repo_last_touched_ts, source_last_touched_ts "
        "FROM detectors.drift WHERE drifted_now = 1"
    ).fetchall()
    return [{"open_divergences": len(rows), "detail": [dict(r) for r in rows]},
            {"answerable_by_code": "partial",
             "reason": "current open divergences are listed above; classifying how each one was "
                       "eventually resolved (fix/duplicate/stall) needs a Haiku pass over the "
                       "follow-up commits, which is not built"}]


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
