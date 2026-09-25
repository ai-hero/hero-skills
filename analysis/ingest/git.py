"""git log of origin/main (or the local default branch) for every fleet repo -> data/git.sqlite.

Read-only: no fetch, no checkout. Standard library only.
"""
import os, re, sqlite3, subprocess, sys, time, datetime as dt

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ingest.fleet import ALL_REPOS, path_of, role_of, dims, OUT
from ingest.redact import redact

DB_PATH = os.path.join(OUT, "git.sqlite")

RS = "\x1e"  # record separator: starts each commit's record
FS = "\x1f"  # field separator: between the fixed-width fields of a record
LOG_FORMAT = FS.join([
    "%H", "%P", "%an", "%ae", "%cn", "%aI", "%cI", "%s",
    "%(trailers:only=true,unfold=true)", "%b",
])

# --no-renames keeps every changed file as a plain add/delete pair (one raw
# line, one numstat line) instead of a single R/C line with two paths, which
# would break the 1:1 zip() below between the raw-status and numstat blocks.
LOG_ARGS = ["--raw", "--numstat", "--no-renames", f"--pretty=format:{RS}{LOG_FORMAT}"]

RAW_RE = re.compile(r"^:\d{6} \d{6} [0-9a-f]+ [0-9a-f]+ ([A-Za-z])\d*\t(.+)$")
NUMSTAT_RE = re.compile(r"^(\d+|-)\t(\d+|-)\t(.+)$")
TRAILER_RE = re.compile(r"^([A-Za-z][A-Za-z-]*): (.+)$")
# Squash bodies concatenate every original commit's trailers, one Claude
# attribution per sub-commit; git's own %(trailers:only=true) keeps just the
# final paragraph, so claude_trailer/trailer_model are read from every
# Co-authored-by line in the body instead of only the parsed trailer block.
CO_AUTHOR_RE = re.compile(r"^co-authored-by: (.+)$", re.I | re.M)
CONV_RE = re.compile(
    r"^(feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert)(\(([^)]+)\))?!?:\s"
)
PR_PAREN_RE = re.compile(r"\(#(\d+)\)\s*$")
PR_MERGE_RE = re.compile(r"^Merge pull request #(\d+)\b")
REVERT_SHA_RE = re.compile(r"This reverts commit ([0-9a-f]{7,40})")
PLAN_ITEM_RE = re.compile(r"\.plans/(?:items/)?0*(\d+)|\bitem\s+#?0*(\d+)\b", re.I)
CLAUDE_MODEL_RE = re.compile(r"(Claude[^<]*)")
BOT_NAME_RE = re.compile(r"(dependabot|github-actions)\[bot\]", re.I)
BOT_EMAIL_RE = re.compile(r"(dependabot|github-actions)", re.I)


def run_git(path, args):
    return subprocess.run(
        ["git", "-C", path] + args,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        encoding="utf-8", errors="replace", check=True,
    ).stdout


def resolve_ref(path):
    """The ref to log, and the plain branch name it points at. Local only: no fetch."""
    try:
        run_git(path, ["rev-parse", "--verify", "-q", "origin/main"])
        return "origin/main", "main"
    except subprocess.CalledProcessError:
        pass
    try:
        out = run_git(path, ["symbolic-ref", "--quiet", "refs/remotes/origin/HEAD"]).strip()
        if out:
            branch = out.rsplit("/", 1)[-1]
            run_git(path, ["rev-parse", "--verify", "-q", f"origin/{branch}"])
            return f"origin/{branch}", branch
    except subprocess.CalledProcessError:
        pass
    branch = run_git(path, ["rev-parse", "--abbrev-ref", "HEAD"]).strip()
    return branch, branch


def parse_tail(tail):
    """Split the trailing %b field's raw text into (body, raw_lines, numstat_lines)."""
    lines = tail.split("\n")
    while lines and lines[-1] == "":
        lines.pop()
    numstat_lines = []
    while lines and NUMSTAT_RE.match(lines[-1]):
        numstat_lines.append(lines.pop())
    numstat_lines.reverse()
    raw_lines = []
    while lines and RAW_RE.match(lines[-1]):
        raw_lines.append(lines.pop())
    raw_lines.reverse()
    return "\n".join(lines), raw_lines, numstat_lines


def parse_commit(chunk):
    fields = chunk.split(FS, 9)
    sha, parents, an, ae, cn, ai, ci, subject, trailer_block = fields[:9]
    tail = fields[9] if len(fields) > 9 else ""
    body, raw_lines, numstat_lines = parse_tail(tail)

    files = []
    for raw_line, num_line in zip(raw_lines, numstat_lines):
        rm = RAW_RE.match(raw_line)
        nm = NUMSTAT_RE.match(num_line)
        status, raw_path = rm.group(1), rm.group(2)
        ins = 0 if nm.group(1) == "-" else int(nm.group(1))
        del_ = 0 if nm.group(2) == "-" else int(nm.group(2))
        path = nm.group(3)
        top_dir = path.split("/", 1)[0] if "/" in path else "(root)"
        _, ext = os.path.splitext(path)
        files.append({
            "path": path, "top_dir": top_dir, "ext": ext.lstrip(".").lower(),
            "insertions": ins, "deletions": del_, "status": status,
        })

    trailers = []
    for line in trailer_block.split("\n"):
        m = TRAILER_RE.match(line)
        if m:
            trailers.append((m.group(1), m.group(2)))

    parent_list = parents.split() if parents else []
    conv = CONV_RE.match(subject)
    conv_type = conv.group(1).lower() if conv else None
    conv_scope = conv.group(3) if conv else None

    pr_number = None
    m = PR_PAREN_RE.search(subject) or PR_MERGE_RE.match(subject)
    if m:
        pr_number = int(m.group(1))

    is_revert = 1 if (conv_type == "revert" or subject.lower().startswith("revert ")) else 0
    rm = REVERT_SHA_RE.search(body)
    reverts_sha = rm.group(1) if rm else None

    claude_trailer, trailer_model = 0, None
    for value in CO_AUTHOR_RE.findall(body):
        if "claude" in value.lower():
            claude_trailer = 1
            mm = CLAUDE_MODEL_RE.search(value)
            if mm and trailer_model is None:
                trailer_model = mm.group(1).strip()

    is_bot = 1 if (BOT_NAME_RE.search(an) or BOT_EMAIL_RE.search(ae)) else 0

    plan_item_ref = None
    pm = PLAN_ITEM_RE.search(subject) or PLAN_ITEM_RE.search(body)
    if pm:
        plan_item_ref = pm.group(1) or pm.group(2)

    d = dims(ai)
    author_domain = ae.split("@", 1)[1].lower() if "@" in ae else None

    commit_row = {
        "sha": sha, "parents": parents, "is_merge": 1 if len(parent_list) > 1 else 0,
        "author_name": an, "author_email_domain": author_domain, "committer_name": cn,
        "authored_ts": d["ts"], "committed_ts": dims(ci)["ts"],
        "day": d["day"], "week": d["week"], "month": d["month"],
        "subject": subject, "body_redacted": redact(body),
        "conv_type": conv_type, "conv_scope": conv_scope, "pr_number": pr_number,
        "files_changed": len(files),
        "insertions": sum(f["insertions"] for f in files),
        "deletions": sum(f["deletions"] for f in files),
        "is_revert": is_revert, "reverts_sha": reverts_sha,
        "claude_trailer": claude_trailer, "trailer_model": trailer_model,
        "is_bot": is_bot, "plan_item_ref": plan_item_ref,
    }
    return commit_row, files, trailers


def iter_commits(repo_output):
    for chunk in repo_output.split(RS)[1:]:
        yield parse_commit(chunk)


def build_db():
    os.makedirs(OUT, exist_ok=True)
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.executescript("""
        CREATE TABLE repos (
            repo TEXT PRIMARY KEY, role TEXT, path TEXT, default_branch TEXT,
            first_commit_ts TEXT, last_commit_ts TEXT, commits INTEGER
        );
        CREATE TABLE commits (
            repo TEXT, sha TEXT, parents TEXT, is_merge INTEGER,
            author_name TEXT, author_email_domain TEXT, committer_name TEXT,
            authored_ts TEXT, committed_ts TEXT, day TEXT, week TEXT, month TEXT,
            subject TEXT, body_redacted TEXT, conv_type TEXT, conv_scope TEXT,
            pr_number INTEGER, files_changed INTEGER, insertions INTEGER, deletions INTEGER,
            is_revert INTEGER, reverts_sha TEXT, claude_trailer INTEGER, trailer_model TEXT,
            is_bot INTEGER, plan_item_ref TEXT,
            PRIMARY KEY (repo, sha)
        );
        CREATE TABLE commit_files (
            repo TEXT, sha TEXT, path TEXT, top_dir TEXT, ext TEXT,
            insertions INTEGER, deletions INTEGER, status TEXT
        );
        CREATE TABLE trailers (repo TEXT, sha TEXT, key TEXT, value TEXT);
        CREATE TABLE meta (source TEXT, path TEXT, rows INTEGER, extracted_at TEXT);
        CREATE INDEX idx_commits_repo ON commits(repo);
        CREATE INDEX idx_commit_files_repo_sha ON commit_files(repo, sha);
        CREATE INDEX idx_trailers_repo_sha ON trailers(repo, sha);
    """)

    unparsed = []
    for repo in ALL_REPOS:
        path = path_of(repo)
        ref, branch = resolve_ref(path)
        output = run_git(path, ["log", ref] + LOG_ARGS)

        first_ts, last_ts, n = None, None, 0
        for commit_row, files, trailer_pairs in iter_commits(output):
            n += 1
            ts = commit_row["authored_ts"]
            if first_ts is None or ts < first_ts:
                first_ts = ts
            if last_ts is None or ts > last_ts:
                last_ts = ts
            cur.execute(
                "INSERT INTO commits VALUES (:repo,:sha,:parents,:is_merge,:author_name,"
                ":author_email_domain,:committer_name,:authored_ts,:committed_ts,:day,:week,"
                ":month,:subject,:body_redacted,:conv_type,:conv_scope,:pr_number,"
                ":files_changed,:insertions,:deletions,:is_revert,:reverts_sha,"
                ":claude_trailer,:trailer_model,:is_bot,:plan_item_ref)",
                {**commit_row, "repo": repo},
            )
            for f in files:
                if f["insertions"] == 0 and f["deletions"] == 0 and f["status"] not in ("A", "D", "M"):
                    unparsed.append(f"{repo} {commit_row['sha'][:8]} unusual file status {f['status']} {f['path']}")
                cur.execute(
                    "INSERT INTO commit_files VALUES (?,?,?,?,?,?,?,?)",
                    (repo, commit_row["sha"], f["path"], f["top_dir"], f["ext"],
                     f["insertions"], f["deletions"], f["status"]),
                )
            for key, value in trailer_pairs:
                cur.execute(
                    "INSERT INTO trailers VALUES (?,?,?,?)", (repo, commit_row["sha"], key, value)
                )

        cur.execute(
            "INSERT INTO repos VALUES (?,?,?,?,?,?,?)",
            (repo, role_of(repo), path, branch, first_ts, last_ts, n),
        )

    now = dt.datetime.now(dt.timezone.utc).isoformat()
    counts = {}
    for table in ("repos", "commits", "commit_files", "trailers"):
        counts[table] = cur.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        cur.execute(
            "INSERT INTO meta VALUES (?,?,?,?)",
            (table, os.path.abspath(__file__), counts[table], now),
        )

    con.commit()
    con.close()
    return counts, unparsed


if __name__ == "__main__":
    t0 = time.time()
    counts, unparsed = build_db()
    elapsed = time.time() - t0
    print(f"git.sqlite: {counts} in {elapsed:.1f}s")
    if unparsed:
        print(f"{len(unparsed)} file rows with an unrecognized status:")
        for line in unparsed[:20]:
            print(f"  {line}")
