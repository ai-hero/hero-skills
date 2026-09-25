"""Q19.xx / RQ-h7-022 -- How accurate are the links between records
(session to PR, co-author trailer to real agent work, subagent to
reviewer persona)? sql half: how many of each link type resolve at all.
Human half: spot-checking whether a resolved link is actually correct.
"""
RQ_ID = "RQ-h7-022"
QUESTION = "How accurate are the links between records (session to PR, co-author trailer to agent work, subagent to reviewer persona)?"


def answer(con):
    total_spend = con.execute("SELECT COUNT(*) AS n FROM detectors.session_spend").fetchone()["n"]
    with_item = con.execute(
        "SELECT COUNT(*) AS n FROM detectors.session_spend WHERE item_id IS NOT NULL"
    ).fetchone()["n"]
    conf = con.execute(
        "SELECT attribution_confidence, COUNT(*) AS n FROM detectors.session_spend GROUP BY attribution_confidence"
    ).fetchall()
    return [{"session_spend_rows": total_spend, "resolved_to_an_item": with_item,
             "resolution_rate": round(with_item / total_spend, 4) if total_spend else None,
             "confidence_breakdown": {r["attribution_confidence"]: r["n"] for r in conf},
             "answerable_by_code": "partial",
             "reason": "link resolution rate is computable; whether a resolved link is actually "
                       "correct (not just present) needs a human spot-check sample"}]


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
