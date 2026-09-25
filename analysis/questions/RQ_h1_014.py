"""Q12.xx / RQ-h1-014 -- Measured in change sets rather than lines or
commits, does each repo's output rank the same way? D1-backed comparison
of three units.
"""
RQ_ID = "RQ-h1-014"
QUESTION = "Measured in change sets rather than lines or commits, does each repo's output rank the same way?"

SQL = """
SELECT c.repo, COUNT(*) AS commits, SUM(c.insertions + c.deletions) AS lines,
       lk.content_hash
FROM git.commits c
LEFT JOIN detectors.changesets_by_commit lk ON lk.repo = c.repo AND lk.sha = c.sha
GROUP BY c.repo
"""


def answer(con):
    rows = con.execute("SELECT repo, sha FROM git.commits").fetchall()
    n_sets_by_hash = dict(con.execute("SELECT content_hash, n_sets FROM detectors.changesets").fetchall())
    links = con.execute("SELECT repo, sha, content_hash FROM detectors.changesets_by_commit").fetchall()
    link_map = {(r["repo"], r["sha"]): r["content_hash"] for r in links}

    by_repo = {}
    for repo, sha in rows:
        h = link_map.get((repo, sha))
        by_repo.setdefault(repo, {"commits": 0, "sets": 0})
        by_repo[repo]["commits"] += 1
        by_repo[repo]["sets"] += n_sets_by_hash.get(h, 1) if h else 1

    lines_by_repo = {r["repo"]: r["lines"] or 0 for r in con.execute(
        "SELECT repo, SUM(insertions + deletions) AS lines FROM git.commits GROUP BY repo"
    ).fetchall()}

    ranked_commits = sorted(by_repo, key=lambda r: -by_repo[r]["commits"])
    ranked_sets = sorted(by_repo, key=lambda r: -by_repo[r]["sets"])
    ranked_lines = sorted(lines_by_repo, key=lambda r: -lines_by_repo[r])

    return [{"repo": r, "commits": by_repo[r]["commits"], "change_sets": by_repo[r]["sets"],
             "lines": lines_by_repo.get(r, 0),
             "rank_by_commits": ranked_commits.index(r) + 1, "rank_by_change_sets": ranked_sets.index(r) + 1,
             "rank_by_lines": ranked_lines.index(r) + 1 if r in ranked_lines else None}
            for r in by_repo]


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
