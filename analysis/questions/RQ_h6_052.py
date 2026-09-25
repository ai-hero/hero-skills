"""Q17.xx / RQ-h6-052 -- How long after a harness feature ships does the
owner start using it, and how often is it later abandoned? sql half:
D10 presence gives per-artifact adoption timestamps; skills/plugin
version history gives ship dates. Abandonment (stopped using after
adopting) needs a human read of whether a gap means abandonment or just
no need.
"""
RQ_ID = "RQ-h6-052"
QUESTION = "How long after a harness feature ships does the owner start using it, and how often is it later abandoned?"


def answer(con):
    rows = con.execute(
        "SELECT artifact, repo, repo_last_touched_ts, source_last_touched_ts FROM detectors.drift"
    ).fetchall()
    return [dict(r) for r in rows] + [
        {"answerable_by_code": "partial",
         "reason": "per-artifact last-touched timestamps (above) show whether a feature is still "
                   "being touched; ship date must be matched by a human to a specific harness "
                   "feature and release, and 'abandoned' vs 'no longer needed' is a judgment call"}
    ]


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
