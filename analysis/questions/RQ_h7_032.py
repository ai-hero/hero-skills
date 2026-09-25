"""Q19.xx / RQ-h7-032 -- When a process change was made to cut token
cost or latency, was the saving measured before and after, or assumed?
sql half: this repo's own spend/session tables give a before/after
split around any known process-change date, which is the mechanism a
real answer would use. No specific process-change date is hardcoded
here since that is fleet-specific and not derivable from the data.
"""
RQ_ID = "RQ-h7-032"
QUESTION = "When a process change was made to cut token cost or latency, was the saving measured before and after, or assumed?"


def answer(con):
    by_repo = con.execute(
        "SELECT repo, SUM(cost_usd) AS total_cost FROM detectors.session_spend GROUP BY repo ORDER BY total_cost DESC"
    ).fetchall()
    return [{"note": "per-repo spend totals below are the raw material for a before/after cut "
                     "around a specific process-change date; no such date is available generically "
                     "here",
             "per_repo_spend": [dict(r) for r in by_repo]},
            {"answerable_by_code": "partial",
             "reason": "the before/after comparison itself needs a human-supplied process-change "
                       "date and a claim of what was assumed to check against"}]


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
