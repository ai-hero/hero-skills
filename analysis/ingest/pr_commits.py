"""The original commits of every merged PR -> .analysis/data/pr_commits.sqlite.

Squash merges put one commit on main per PR; the commits the work was
actually made in survive only at GitHub's refs/pull/N/head. This mirrors
each fleet repo's remote (refs/pull/* included) into .analysis/data/mirrors/
and reads, for every merged PR, the commits between the PR head and the
main commit it branched from. The fleet's own checkouts are never touched.

Network: one `git clone --mirror` per repo the first time, `git fetch` after.
No GitHub API calls, so no rate-limit budget is spent.
"""
import json, os, sqlite3, subprocess, sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ingest.fleet import ALL_REPOS, path_of, OUT
from ingest.git import LOG_ARGS, iter_commits

DB_PATH = os.path.join(OUT, "pr_commits.sqlite")
MIRRORS = os.path.join(OUT, "mirrors")


def git(path, args, check=True):
    return subprocess.run(["git", "-C", path] + args, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          encoding="utf-8", errors="replace", check=check).stdout


def mirror(repo):
    dest = os.path.join(MIRRORS, f"{repo}.git")
    if os.path.isdir(dest):
        git(dest, ["fetch", "--prune", "--quiet", "origin"])
        return dest
    url = git(path_of(repo), ["remote", "get-url", "origin"]).strip()
    os.makedirs(MIRRORS, exist_ok=True)
    subprocess.run(["git", "clone", "--mirror", "--quiet", url, dest], check=True, capture_output=True, text=True)
    return dest


def pr_log(m, rng):
    """Commits in rng, oldest first, parsed exactly as ingest/git.py parses main."""
    out = git(m, ["log"] + LOG_ARGS + rng, check=False)
    return list(reversed(list(iter_commits(out))))


def build(only=None):
    gcon = sqlite3.connect(os.path.join(OUT, "git.sqlite"))
    hcon = sqlite3.connect(os.path.join(OUT, "github.sqlite"))
    con = sqlite3.connect(DB_PATH)
    if not only:
        con.executescript("DROP TABLE IF EXISTS pr_commits; DROP TABLE IF EXISTS pr_coverage;")
    con.executescript("""
        CREATE TABLE IF NOT EXISTS pr_commits (
            repo TEXT, pr_number INTEGER, idx INTEGER, sha TEXT, is_merge INTEGER,
            author TEXT, ts TEXT, subject TEXT, body_redacted TEXT, claude_trailer INTEGER,
            files_json TEXT, insertions INTEGER, deletions INTEGER,
            PRIMARY KEY (repo, pr_number, sha)
        );
        CREATE TABLE IF NOT EXISTS pr_coverage (
            repo TEXT, pr_number INTEGER, main_sha TEXT, github_commits INTEGER,
            recovered INTEGER, how TEXT, PRIMARY KEY (repo, pr_number)
        );
    """)
    for repo in ALL_REPOS:
        if only and repo not in only:
            continue
        try:
            m = mirror(repo)
        except subprocess.CalledProcessError as e:
            print(f"{repo}: mirror failed: {e.stderr.strip()[:200]}", file=sys.stderr)
            # Rows from an earlier run stay; only PRs with no coverage row are marked, so the gap can be queried.
            con.executemany("INSERT OR IGNORE INTO pr_coverage VALUES (?,?,?,?,?,?)", [
                (repo, number, None, gh_commits, 0, "mirror failed") for number, gh_commits in hcon.execute(
                    "SELECT number, commits FROM prs WHERE repo=? AND merged_ts IS NOT NULL", (repo,))])
            con.commit()
            continue
        con.execute("DELETE FROM pr_commits WHERE repo=?", (repo,))
        con.execute("DELETE FROM pr_coverage WHERE repo=?", (repo,))
        refs = set(git(m, ["for-each-ref", "--format=%(refname)", "refs/pull/"]).split())
        main = {n: (sha, parents) for n, sha, parents in gcon.execute(
            "SELECT pr_number, sha, parents FROM commits WHERE repo=? AND pr_number IS NOT NULL", (repo,))}
        prs = hcon.execute("SELECT number, commits FROM prs WHERE repo=? AND merged_ts IS NOT NULL", (repo,)).fetchall()
        n_ok = 0
        for number, gh_commits in prs:
            ref = f"refs/pull/{number}/head"
            main_sha, parents = main.get(number, (None, ""))
            if ref not in refs:
                how, commits = "no pull ref", []
            else:
                # The branch point is main just before the PR landed: the squash
                # commit's (first) parent. Without a main commit, fall back to
                # GitHub's own commit count from the head.
                if parents:
                    rng = [ref, "^" + parents.split()[0]]
                    how = "head since main parent"
                else:
                    rng = [f"-n{gh_commits or 1}", ref]
                    how = "head, github count"
                commits = pr_log(m, rng)
                if gh_commits and len(commits) > gh_commits:
                    # A branch that merged main in pulls main's history along; keep the newest N.
                    commits = commits[-gh_commits:]
            for i, (c, files, _) in enumerate(commits):
                con.execute("INSERT OR REPLACE INTO pr_commits VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)", (
                    repo, number, i, c["sha"], c["is_merge"], c["author_name"], c["authored_ts"], c["subject"],
                    c["body_redacted"], c["claude_trailer"],
                    json.dumps([{"path": f["path"], "ins": f["insertions"], "del": f["deletions"]} for f in files]),
                    c["insertions"], c["deletions"]))
            con.execute("INSERT OR REPLACE INTO pr_coverage VALUES (?,?,?,?,?,?)",
                        (repo, number, main_sha, gh_commits, len(commits), how))
            n_ok += bool(commits)
        con.commit()
        print(f"{repo}: {n_ok}/{len(prs)} merged PRs recovered", file=sys.stderr)
    con.close()


if __name__ == "__main__":
    build(set(sys.argv[1:]) or None)
