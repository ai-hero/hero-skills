"""Q13.xx / RQ-h4-020 -- When scope or a convention moves from one repo
to another, does either repo's design record say which repo now owns
it? sql half: D3 propagation gives the repo pairs where an actual
convention/config move happened; D2 drift gives whether each side's
design record is stale. Whether the design record's *text* names the
new owner is a per-file human or Haiku read, not built here.
"""
RQ_ID = "RQ-h4-020"
QUESTION = "When scope or a convention moves from one repo to another, does either repo's design record say which repo now owns it?"


def answer(con):
    pairs = con.execute(
        "SELECT upstream_repo, downstream_repo, COUNT(*) AS moves FROM detectors.propagation "
        "GROUP BY upstream_repo, downstream_repo ORDER BY moves DESC"
    ).fetchall()
    drift = con.execute(
        "SELECT repo, artifact, drifted_now FROM detectors.drift"
    ).fetchall()
    return [{"convention_move_pairs": [dict(r) for r in pairs],
             "design_record_staleness_by_repo": [dict(r) for r in drift]},
            {"answerable_by_code": "partial",
             "reason": "which repo pairs actually moved a convention, and whether each side's design "
                       "record is currently stale, are both computed above; whether the record's own "
                       "text names the new owner needs a human or Haiku read of that text"}]


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
