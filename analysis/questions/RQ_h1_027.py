"""Q9.xx / RQ-h1-027 -- When two agent sessions work in the same repo at
once, how often does it happen, per repo? Same interval-overlap method as
RQ-h6-019, scoped to overlaps within one repo (a same-repo overlap is the
collision risk; a fleet-wide overlap across different repos isn't). Doesn't
say whether they ran in separate worktrees -- sessions carries no worktree
path, only git_branches.
"""
RQ_ID = "RQ-h1-027"
QUESTION = "When two agent sessions work in the same repo at once, how often does it happen, per repo?"


def answer(con):
    rows = con.execute(
        "SELECT repo, first_ts, last_ts FROM harness.sessions WHERE first_ts IS NOT NULL AND last_ts IS NOT NULL"
    ).fetchall()
    by_repo = {}
    for r in rows:
        by_repo.setdefault(r["repo"], []).append((r["first_ts"], r["last_ts"]))

    out = []
    for repo, windows in by_repo.items():
        windows.sort()
        overlaps = 0
        for i in range(len(windows) - 1):
            if windows[i][1] > windows[i + 1][0]:
                overlaps += 1
        out.append({"repo": repo, "sessions": len(windows), "overlapping_pairs": overlaps})
    return sorted(out, key=lambda x: -x["overlapping_pairs"])


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
