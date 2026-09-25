"""Q3.04 / RQ-h6-043 -- How often does a task run in an isolated worktree
versus the shared checkout, and do shared checkouts produce collisions?
No worktree-path field is ingested, so "isolated worktree" isn't directly
observable -- proxy: a session touching exactly one branch reads as
plausibly isolated task scope; a session touching several branches at once
is the shared-checkout risk pattern (same one D9's session_spend flags as
low-confidence attribution). Collisions checked via RQ-h1-027's same-repo
session-overlap count.
"""
RQ_ID = "RQ-h6-043"
QUESTION = "How often does a task run in an isolated worktree versus the shared checkout, and do collisions happen?"


def answer(con):
    rows = con.execute("SELECT session_id_hash, git_branches FROM harness.sessions").fetchall()
    import json
    single, multi = 0, 0
    for r in rows:
        try:
            branches = json.loads(r["git_branches"]) or []
        except (json.JSONDecodeError, TypeError):
            branches = []
        if len(branches) <= 1:
            single += 1
        else:
            multi += 1
    from questions.RQ_h1_027 import answer as overlap_answer
    overlap_rows = overlap_answer(con)
    total_overlaps = sum(r.get("overlapping_pairs", 0) for r in overlap_rows if "overlapping_pairs" in r)
    return [{"single_branch_sessions": single, "multi_branch_sessions": multi,
             "same_repo_session_overlaps": total_overlaps}]


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
