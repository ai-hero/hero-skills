"""Q15.xx / RQ-h5-005 -- How many violations has an automated style or
lint gate caught, and how many later turned out to be false positives?
sql half: gate_firings for lint/style-kind gates, by verdict. Whether a
failure was a genuine violation or a false positive needs reading the
follow-up commit (did the "fix" actually change the flagged code, or
just silence/skip the check), which is not classified here.
"""
RQ_ID = "RQ-h5-005"
QUESTION = "How many violations has an automated style/lint gate caught, and how many later turned out to be false positives?"


def answer(con):
    rows = con.execute(
        "SELECT gate_kind, verdict, COUNT(*) AS n FROM detectors.gate_firings "
        "WHERE gate_kind LIKE '%lint%' OR gate_kind LIKE '%style%' OR gate_kind LIKE '%format%' "
        "GROUP BY 1, 2"
    ).fetchall()
    return [{"lint_style_gate_verdicts": [dict(r) for r in rows]},
            {"answerable_by_code": "partial",
             "reason": "failure counts by lint/style gate are above; distinguishing a genuine "
                       "violation from a false positive needs reading whether the follow-up commit "
                       "actually changed the flagged code vs. silenced the check, which this repo "
                       "does not classify"}]


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
