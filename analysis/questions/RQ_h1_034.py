"""Q9.xx / RQ-h1-034 -- Does a work item map to exactly one merged change,
or to zero or several? Uses commits.plan_item_ref (bare number, repo-scoped
here) as the only item<->commit link -- the same chain NEW-A-01
documents, present only where a commit cites an item.
"""
RQ_ID = "RQ-h1-034"
QUESTION = "Does a work item map to exactly one merged change, or to zero or several?"

SQL = """
SELECT repo, plan_item_ref, COUNT(*) AS commits
FROM git.commits
WHERE plan_item_ref IS NOT NULL AND pr_number IS NOT NULL
GROUP BY repo, plan_item_ref
"""


def answer(con):
    rows = con.execute(SQL).fetchall()
    counts = sorted(r["commits"] for r in rows)
    n = len(counts)
    exactly_one = sum(1 for c in counts if c == 1)
    return [{
        "item_refs_with_a_linked_merged_commit": n,
        "mapped_to_exactly_one_commit": exactly_one,
        "mapped_to_several": n - exactly_one,
        "max_commits_for_one_item": counts[-1] if n else None,
        "note": "coverage is low by construction -- see NEW-A-01",
    }]


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
