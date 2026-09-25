"""Q13.xx / RQ-h4-007 -- When a decision is meant to hold identically
across clones, do the clones' design records actually agree? Proxy:
design_decisions headings that appear in more than one repo (same
heading text = same intended-shared decision), checked for identical
text_redacted across those repos.
"""
RQ_ID = "RQ-h4-007"
QUESTION = "When a decision is meant to hold identically across clones, do the clones' design records agree?"


def answer(con):
    rows = con.execute("SELECT repo, heading, text_redacted FROM knowledge.design_decisions").fetchall()
    by_heading = {}
    for r in rows:
        by_heading.setdefault(r["heading"], []).append((r["repo"], r["text_redacted"]))
    shared = {h: v for h, v in by_heading.items() if len(v) > 1}
    agree = sum(1 for h, v in shared.items() if len({t for _, t in v}) == 1)
    return [{"headings_appearing_in_multiple_repos": len(shared), "with_identical_text_everywhere": agree}]


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
