"""Q10.xx / RQ-h6-009 -- How often is the roadmap refresh run on each repo,
and do longer gaps go with more stale work? Proxy: wayfare-sync-plan skill
invocations (harness.tool_calls.skill_name) per repo, gaps between them in
days. Reported as gaps between invocations, not as a rate.
"""
RQ_ID = "RQ-h6-009"
QUESTION = "How often is the roadmap refresh run on each repo, and do longer gaps go with more stale work?"

SQL = """
SELECT s.repo, t.ts
FROM harness.tool_calls t
JOIN harness.sessions s ON s.session_id_hash = t.session_id_hash
WHERE t.skill_name LIKE '%wayfare-sync-plan%'
ORDER BY s.repo, t.ts
"""


def answer(con):
    rows = con.execute(SQL).fetchall()
    if not rows:
        return [{"note": "no wayfare-sync-plan invocations recorded"}]
    import datetime as dt
    by_repo = {}
    for r in rows:
        by_repo.setdefault(r["repo"], []).append(r["ts"])
    out = []
    for repo, times in by_repo.items():
        gaps = []
        for a, b in zip(times, times[1:]):
            gaps.append((dt.datetime.fromisoformat(b.replace("Z", "+00:00")) -
                          dt.datetime.fromisoformat(a.replace("Z", "+00:00"))).days)
        out.append({"repo": repo, "runs": len(times), "gap_days": gaps})
    return out


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
