"""Q13.xx / NEW-C07-C -- How long does a disagreement between clones'
records of a shared decision persist before it's reconciled? Proxy:
RQ-h4-007's headings that DON'T agree everywhere -- no timestamp for when
they started disagreeing or when (if ever) they converge, so only the
current-state count is answerable, not a duration.
"""
RQ_ID = "NEW-C07-C"
QUESTION = "How long does a disagreement between clones' records of a shared decision persist?"


def answer(con):
    rows = con.execute("SELECT repo, heading, text_redacted, first_seen_ts FROM knowledge.design_decisions").fetchall()
    by_heading = {}
    for r in rows:
        by_heading.setdefault(r["heading"], []).append(r)
    disagreeing = {h: v for h, v in by_heading.items() if len(v) > 1 and len({x["text_redacted"] for x in v}) > 1}
    return [{"headings_currently_disagreeing": len(disagreeing),
             "note": "no start/converge timestamps exist to measure persistence duration -- current-state count only"}]


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
