"""Q13.xx / RQ-h4-026 -- For a fact meant to be identical everywhere it's
stated (a config constant, a baseline dependency version), how often do
the copies actually agree? Proxy: fleet.BASELINE_CUTOFF-independent check
-- each repo's instruction_files.vendored_hash for .claude/rules/
comments.md, same source as D2 drift, reframed as "how many copies agree"
rather than "does the newest one match."
"""
RQ_ID = "RQ-h4-026"
QUESTION = "For a fact meant to be identical everywhere, how often do the copies actually agree?"


def answer(con):
    rows = con.execute(
        "SELECT vendored_hash, COUNT(*) AS n FROM knowledge.instruction_files "
        "WHERE path = '.claude/rules/comments.md' GROUP BY vendored_hash ORDER BY n DESC"
    ).fetchall()
    total = sum(r["n"] for r in rows)
    largest_group = rows[0]["n"] if rows else 0
    return [{"repos_carrying_a_copy": total, "distinct_versions": len(rows),
             "largest_agreeing_group": largest_group,
             "agreement_share": round(largest_group / total, 3) if total else None}]


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
