"""Q10.xx / NEW-C05-03 -- How often does one review persona find a
defect that every other persona on the same PR missed? No per-persona
review-comment table is ingested (only aggregate review_count on the
PR, and gate_firings by actor); a real answer needs a Haiku read of
each review-persona's comment against the others on the same PR.
"""
RQ_ID = "NEW-C05-03"
QUESTION = "How often does one review persona find a defect that every other persona on the same PR missed?"


def answer(con):
    actors = con.execute(
        "SELECT actor, COUNT(*) AS n FROM detectors.gate_firings GROUP BY actor ORDER BY n DESC"
    ).fetchall()
    return [{"gate_actors_seen": [dict(r) for r in actors]},
            {"answerable_by_code": False,
             "reason": "gate actors are the closest ingested proxy for 'personas', but which one "
                       "uniquely caught a given defect needs comparing per-persona review comments "
                       "on the same PR, which is not ingested at that granularity"}]


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
