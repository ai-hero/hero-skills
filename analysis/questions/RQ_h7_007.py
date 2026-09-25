"""Q4.09 / RQ-h7-007 -- When the owner disagrees with the agent's
proposal, what form does it take (correction, interruption, takeover,
abandonment), and whose position wins? Haiku-backed. "Interruption/
takeover/abandonment" aren't kinds the classifier produces (it only
labels correction/approval/redirect/question/other) -- "whose position
wins" isn't answerable from prompt text alone either. Reports what the
classifier actually supports: the correction/redirect share, which is
the "disagreement, in some form" signal.
"""
RQ_ID = "RQ-h7-007"
QUESTION = "When the owner disagrees with the agent's proposal, what form does it take?"


def answer(con):
    rows = con.execute(
        "SELECT pk.kind, COUNT(*) AS n FROM detectors.prompt_kind_by_prompt p "
        "JOIN detectors.prompt_kind pk ON pk.content_hash = p.content_hash "
        "WHERE p.flagged = 1 GROUP BY pk.kind ORDER BY n DESC"
    ).fetchall()
    return [dict(r) for r in rows] + [{
        "note": "the classifier's kinds are correction/approval/redirect/question/other, "
                "not interruption/takeover/abandonment -- 'whose position wins' isn't "
                "answerable from prompt text alone",
    }]


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
