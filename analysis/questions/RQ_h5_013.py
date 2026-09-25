"""Q14.xx / RQ-h5-013 -- Can a change to the control register bypass the
audit, for example by a direct edit that never runs the checkers? Proxy:
register_history commits whose subject doesn't mention "sync"/"audit"/
"consistency" (i.e. a change to CONTROLS.yaml/CHECKS.yaml outside the
normal regenerate-and-commit flow).
"""
RQ_ID = "RQ-h5-013"
QUESTION = "Can a change to the control register bypass the audit, e.g. a direct edit?"


def answer(con):
    shas = [r[0] for r in con.execute("SELECT DISTINCT sha FROM knowledge.register_history").fetchall()]
    if not shas:
        return [{"note": "no register_history rows"}]
    unmatched = outside_flow = 0
    for sha in shas:
        row = con.execute("SELECT subject FROM v_commits WHERE sha = ? LIMIT 1", (sha,)).fetchone()
        if not row:
            unmatched += 1
        elif not any(w in row["subject"].lower() for w in ("sync", "audit", "consistency", "checker")):
            outside_flow += 1
    return [{"register_history_commits": len(shas), "unmatched_to_git_commits": unmatched,
             "matched_but_no_sync_audit_language": outside_flow}]


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
