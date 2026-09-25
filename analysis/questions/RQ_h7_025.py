"""Q19.xx / RQ-h7-025 -- How biased is the defect data by counting only
what was found, fixed and described by its own author? sql half: how
much of the defect record (duplicate_fixes, gate_firings failures) is
attributable to the same actor who introduced the issue, vs a separate
reviewer/gate. Human half: whether that self-report share understates
the true defect rate. D8 never writes a 'fail' verdict: a gate that
caught something is CHANGES_REQUESTED (review) or 'caught' (CI).
"""
RQ_ID = "RQ-h7-025"
QUESTION = "How biased is the defect data by counting only what was found, fixed, and described by its own author?"


def answer(con):
    dup = con.execute("SELECT COUNT(*) AS n FROM detectors.duplicate_fixes").fetchone()["n"]
    gate_fail = con.execute(
        "SELECT COUNT(*) AS n FROM detectors.gate_firings WHERE verdict IN ('CHANGES_REQUESTED', 'caught')"
    ).fetchone()["n"]
    gate_by_actor = con.execute(
        "SELECT gate_kind, actor, COUNT(*) AS n FROM detectors.gate_firings "
        "WHERE verdict IN ('CHANGES_REQUESTED', 'caught') GROUP BY gate_kind, actor ORDER BY n DESC LIMIT 10"
    ).fetchall()
    return [{"duplicate_fixes_recorded": dup, "gate_failures_recorded": gate_fail,
             "gate_failures_by_actor_top10": [dict(r) for r in gate_by_actor],
             "answerable_by_code": "partial",
             "reason": "what got caught by a gate (an independent check) vs what the same author "
                       "self-fixed without one is computable per above; whether the defects nobody "
                       "caught outnumber these is not observable from this data"}]


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
