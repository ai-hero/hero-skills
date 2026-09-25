"""Q10.xx / NEW-C05-02 -- Of all agent mistakes found, what share did
the agent record itself, versus found by review agents, versus found
by the owner? sql half: gate_firings by actor as a proxy for "who
caught it" when a gate exists; there is no ingested table that
separates self-recorded mistakes from owner-found ones outside of gate
data.
"""
RQ_ID = "NEW-C05-02"
QUESTION = "Of all agent mistakes found, what share did the agent record itself, review agents find, or the owner find?"


def answer(con):
    by_actor = con.execute(
        "SELECT actor, COUNT(*) AS n FROM detectors.gate_firings WHERE verdict = 'fail' GROUP BY actor ORDER BY n DESC"
    ).fetchall()
    corrections = con.execute(
        "SELECT COUNT(*) AS n FROM detectors.prompt_kind WHERE kind = 'correction'"
    ).fetchone()["n"]
    return [{"gate_failures_by_actor": [dict(r) for r in by_actor],
             "owner_correction_prompts": corrections},
            {"answerable_by_code": "partial",
             "reason": "gate failures by actor and owner-correction prompt counts are above as "
                       "proxies; there is no direct 'agent self-recorded its own mistake' table, "
                       "which would need a Haiku read of session logs for self-reported errors"}]


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
