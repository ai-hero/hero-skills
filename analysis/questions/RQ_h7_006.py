"""Q4.05 / RQ-h7-006 -- How often does an agent stop to ask the owner a
question, and how often is the answer agree, push back, or redirect?
harness.asks count directly; the answer classification reuses the Haiku
prompt_kind labels for the owner's NEXT prompt after each ask (an
approximation -- the next prompt isn't guaranteed to be the direct answer
to that specific ask).
"""
RQ_ID = "RQ-h7-006"
QUESTION = "How often does an agent stop to ask the owner a question, and how does the owner respond?"


def answer(con):
    total_asks = con.execute("SELECT COUNT(*) FROM harness.asks").fetchone()[0]
    asks_ts = [r[0] for r in con.execute("SELECT ts FROM harness.asks WHERE ts IS NOT NULL").fetchall()]
    kinds = {}
    for ts in asks_ts:
        row = con.execute(
            "SELECT pk.kind FROM harness.prompts hp "
            "JOIN detectors.prompt_kind_by_prompt pk2 ON pk2.repo = hp.repo AND pk2.ts = hp.ts "
            "JOIN detectors.prompt_kind pk ON pk.content_hash = pk2.content_hash "
            "WHERE hp.ts > ? ORDER BY hp.ts LIMIT 1", (ts,),
        ).fetchone()
        if row:
            kinds[row[0]] = kinds.get(row[0], 0) + 1
    return [{"total_asks": total_asks, "next_prompt_kind_distribution": kinds,
             "note": "approximate -- matches the owner's next prompt after an ask, not a confirmed direct answer"}]


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
