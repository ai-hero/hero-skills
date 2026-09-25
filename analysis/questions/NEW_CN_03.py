"""Q3.xx / NEW-CN-03 -- How far do non-code repos (design exports,
reconciliation documents) drift from the code that implements them?
D2 drift already answers exactly this for the design-system repo; alias
it. Whether the drift is *acceptable* for a given repo pair is a human
judgment D2 doesn't make.
"""
RQ_ID = "NEW-CN-03"
QUESTION = "How far do non-code repos drift from the code that implements them?"


def answer(con):
    rows = con.execute(
        "SELECT artifact, repo, drifted_now, repo_last_touched_ts, source_last_touched_ts "
        "FROM detectors.drift ORDER BY drifted_now DESC"
    ).fetchall()
    return [dict(r) for r in rows] + [
        {"answerable_by_code": "partial",
         "reason": "D2 tracks drift for the artifacts it was pointed at (the design-system repo); "
                   "a fleet with other non-code sources (Figma exports, spec docs) not wired into "
                   "D2 needs a human to point the detector at them first"}
    ]


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
