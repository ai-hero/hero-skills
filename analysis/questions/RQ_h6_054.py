"""Q3.08 / RQ-h6-054 -- Does context compaction in a session correlate with
a later human correction in the same session? No dedicated compaction
event/tool exists in the harness tables -- proxy: a turn whose text
mentions "compact", checked for a Haiku-classified
correction/redirect prompt later in the SAME session.
"""
RQ_ID = "RQ-h6-054"
QUESTION = "Does context compaction in a session correlate with a later human correction in the same session?"


def answer(con):
    compactions = con.execute(
        "SELECT session_id_hash, ts FROM harness.turns WHERE text_redacted LIKE '%compact%'"
    ).fetchall()
    if not compactions:
        return [{"note": "no compaction-mentioning turns found"}]

    followed_by_correction = 0
    for c in compactions:
        row = con.execute(
            "SELECT 1 FROM harness.prompts hp "
            "JOIN detectors.prompt_kind_by_prompt pk ON pk.repo = hp.repo AND pk.ts = hp.ts "
            "JOIN detectors.prompt_kind k ON k.content_hash = pk.content_hash "
            "WHERE hp.ts > ? AND k.kind IN ('correction', 'redirect') LIMIT 1",
            (c["ts"],),
        ).fetchone()
        followed_by_correction += bool(row)
    return [{"compaction_events": len(compactions), "followed_by_a_correction_prompt_anywhere_later": followed_by_correction,
             "note": "not scoped to the same session (prompts aren't session-linked in this table) -- "
                     "reads as 'anywhere later in the fleet,' an overcount, not a per-session rate"}]


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
