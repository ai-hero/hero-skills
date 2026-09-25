"""Q12.xx / RQ-h1-005 -- Within one repo, when one side of a paired
contract changes (a backend route, a frontend client), does the other
side get updated in the same change? Proxy: commits touching both a
`service/`-or-`lib/`-rooted path and a `ui/`-rooted path in the same
commit, as a share of commits touching either.
"""
RQ_ID = "RQ-h1-005"
QUESTION = "When one side of a paired contract changes, does the other side get updated in the same change?"


def answer(con):
    rows = con.execute(
        "SELECT repo, sha, GROUP_CONCAT(DISTINCT top_dir) AS dirs FROM git.commit_files "
        "WHERE top_dir IN ('service', 'lib', 'ui') GROUP BY repo, sha"
    ).fetchall()
    total = len(rows)
    both = sum(1 for r in rows if "ui" in r["dirs"].split(",") and ("service" in r["dirs"] or "lib" in r["dirs"]))
    return [{"commits_touching_backend_or_frontend": total, "touching_both_sides": both,
             "both_sides_share": round(both / total, 3) if total else None}]


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
