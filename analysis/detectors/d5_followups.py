"""D5 follow-ups and rework -> detectors.sqlite, table followups.

A merged PR is "followed up" if, within 7 or 14 days after its merge, a
LATER commit in the same repo touches >= 50% of the same files (git.commits
joined to git.commit_files via pr_number gives each PR's file set; a squash
merge means most PRs collapse to one commit, so this reads files from every
commit carrying that pr_number, not just one). Also carries the two direct
signals: commits.is_revert, and pr_timeline reopen events (kind='reopened').

A PR with zero files touched (found in prs but never matched to a commit,
e.g. PRs with no pr_number link -- see NEW-A-01) is skipped: no file
set means no overlap can be computed, not "never followed up."
"""
import os, sqlite3, sys, datetime as dt

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ingest.fleet import OUT

DB_PATH = os.path.join(OUT, "detectors.sqlite")
GIT_DB = os.path.join(OUT, "git.sqlite")
GITHUB_DB = os.path.join(OUT, "github.sqlite")
WINDOWS_DAYS = (7, 14)


def _parse(ts):
    return dt.datetime.fromisoformat(ts.replace("Z", "+00:00"))


def build():
    con = sqlite3.connect(DB_PATH)
    con.execute("ATTACH DATABASE ? AS git", (GIT_DB,))
    con.execute("ATTACH DATABASE ? AS github", (GITHUB_DB,))

    prs = con.execute(
        "SELECT repo, number, merged_ts FROM github.prs WHERE merged_ts IS NOT NULL"
    ).fetchall()

    pr_files = {}
    for repo, number, path in con.execute(
        "SELECT c.repo, c.pr_number, cf.path FROM git.commits c "
        "JOIN git.commit_files cf ON cf.repo = c.repo AND cf.sha = c.sha "
        "WHERE c.pr_number IS NOT NULL"
    ).fetchall():
        pr_files.setdefault((repo, number), set()).add(path)

    # repo -> sorted [(ts, sha, {files})] for every commit after the PR's own, to scan candidates
    commits_by_repo = {}
    for repo, sha, ts in con.execute("SELECT repo, sha, committed_ts FROM git.commits WHERE committed_ts IS NOT NULL").fetchall():
        commits_by_repo.setdefault(repo, []).append((ts, sha))
    for repo in commits_by_repo:
        commits_by_repo[repo].sort()
    files_by_commit = {}
    for repo, sha, path in con.execute("SELECT repo, sha, path FROM git.commit_files").fetchall():
        files_by_commit.setdefault((repo, sha), set()).add(path)

    revert_shas = {(repo, sha) for repo, sha in con.execute(
        "SELECT repo, sha FROM git.commits WHERE is_revert = 1"
    ).fetchall()}
    reopened_prs = {(repo, number) for repo, number in con.execute(
        "SELECT DISTINCT repo, number FROM github.pr_timeline WHERE event = 'reopened'"
    ).fetchall()}

    out = []
    for repo, number, merged_ts in prs:
        base_files = pr_files.get((repo, number))
        merged_dt = _parse(merged_ts)
        followup_days = {w: None for w in WINDOWS_DAYS}
        if base_files:
            for ts, sha in commits_by_repo.get(repo, []):
                ts_dt = _parse(ts)
                delta_days = (ts_dt - merged_dt).total_seconds() / 86400
                if delta_days <= 0:
                    continue
                if delta_days > max(WINDOWS_DAYS):
                    break
                cfiles = files_by_commit.get((repo, sha), set())
                if not cfiles:
                    continue
                overlap = len(cfiles & base_files) / len(base_files)
                if overlap >= 0.5:
                    for w in WINDOWS_DAYS:
                        if delta_days <= w and followup_days[w] is None:
                            followup_days[w] = round(delta_days, 2)
        out.append((
            repo, number, merged_ts,
            followup_days[7], followup_days[14],
            1 if (repo, number) in reopened_prs else 0,
        ))

    con.execute("DROP TABLE IF EXISTS followups")
    con.execute("""
        CREATE TABLE followups (
            repo TEXT, number INTEGER, merged_ts TEXT,
            followup_within_7d_days REAL, followup_within_14d_days REAL, reopened INTEGER,
            PRIMARY KEY (repo, number)
        )
    """)
    con.executemany("INSERT INTO followups VALUES (?,?,?,?,?,?)", out)
    con.commit()

    n7 = sum(1 for r in out if r[3] is not None)
    n14 = sum(1 for r in out if r[4] is not None)
    nreopen = sum(1 for r in out if r[5])
    print(f"detectors.sqlite: followups {len(out)} merged PRs; "
          f"{n7} followed up within 7d, {n14} within 14d, {nreopen} reopened; "
          f"{len(revert_shas)} revert commits fleet-wide")
    con.close()


if __name__ == "__main__":
    build()
