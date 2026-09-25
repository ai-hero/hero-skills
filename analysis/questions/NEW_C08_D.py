"""Q16.xx / NEW-C08-D -- How many commits tighten versus loosen a CI
gate, and do they cluster around audit sweeps or follow incidents? sql
half: conv_type/subject keyword proxy on commits touching CI config
paths, bucketed tighten/loosen/neutral by keyword. Whether a cluster
lines up with a specific audit sweep or incident needs a human to
cross-reference dates.
"""
RQ_ID = "NEW-C08-D"
QUESTION = "How many commits tighten versus loosen a CI gate, and do they cluster around audit sweeps or incidents?"

_TIGHTEN = ["require", "enforce", "strict", "block", "fail on", "add check", "gate"]
_LOOSEN = ["allow", "skip", "disable", "loosen", "relax", "bypass", "ignore"]


def answer(con):
    rows = con.execute(
        "SELECT DISTINCT c.repo, c.sha, c.subject, c.committed_ts FROM git.commits c "
        "JOIN git.commit_files f ON f.repo = c.repo AND f.sha = c.sha "
        "WHERE f.top_dir = '.github'"
    ).fetchall()
    tighten = loosen = neutral = 0
    for r in rows:
        s = (r["subject"] or "").lower()
        if any(kw in s for kw in _TIGHTEN):
            tighten += 1
        elif any(kw in s for kw in _LOOSEN):
            loosen += 1
        else:
            neutral += 1
    return [{"ci_config_commits": len(rows), "tighten_by_keyword": tighten,
             "loosen_by_keyword": loosen, "neutral_or_unclear": neutral,
             "answerable_by_code": "partial",
             "reason": "tighten/loosen is a subject-line keyword proxy, not a verified diff read; "
                       "clustering around a specific audit sweep or incident needs a human to line "
                       "up dates with actual audit/incident records"}]


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
