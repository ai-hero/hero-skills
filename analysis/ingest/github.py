"""GitHub PRs, reviews, timeline events and CI runs -> data/github.sqlite.

Read-only: every call here is `gh pr list`, `gh run list`, or a GET through
`gh api`. Nothing pushes, merges, comments, or writes to GitHub.
"""
import datetime as dt
import json
import os
import re
import sqlite3
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ingest.fleet import ALL_REPOS, path_of, dims, OUT
from ingest.redact import redact

DB_PATH = os.path.join(OUT, "github.sqlite")

WORKERS = 4              # lower than gh's own default concurrency guidance: a prior
                         # run at 10 workers tripped GitHub's secondary rate limit
                         # across ~13 repos' PR-detail + timeline fan-out
MIN_CORE_REMAINING = 500       # abort rather than grind the REST quota to empty
MIN_GRAPHQL_REMAINING = 500
TIMING_RUN_CAP = 300     # at most the last N runs per repo get a billable-minutes call
TIMING_BUDGET_S = 600    # ci_jobs is best-effort; stop pulling timings past this


def check_rate_limit():
    """Abort before doing any work if quota is already low, instead of
    burning through it and tripping GitHub's secondary rate limit mid-run."""
    data = gh_json(["api", "rate_limit"])
    if data is None:
        print("  ! could not read gh rate_limit; proceeding cautiously", file=sys.stderr)
        return
    core = data.get("resources", {}).get("core", {})
    gql = data.get("resources", {}).get("graphql", {})
    print(f"  rate limit: core {core.get('remaining')}/{core.get('limit')}, "
          f"graphql {gql.get('remaining')}/{gql.get('limit')}")
    if core.get("remaining", 9999) < MIN_CORE_REMAINING or gql.get("remaining", 9999) < MIN_GRAPHQL_REMAINING:
        reset = dt.datetime.fromtimestamp(core.get("reset", 0), dt.timezone.utc)
        sys.exit(f"gh rate limit too low to start a full ingest (core={core.get('remaining')}, "
                 f"graphql={gql.get('remaining')}); resets {reset.isoformat()}")

TIMELINE_EVENTS = {
    "ready_for_review", "review_requested", "labeled",
    "head_ref_force_pushed", "merged", "closed", "reopened",
}

# gh's PR/review JSON gives a login, not an is_bot flag, for reviewers and
# timeline actors, so bot detection there is a login-shape heuristic.
BOT_LOGIN_RE = re.compile(r"(\[bot\]$|^app/|-bot$|^dependabot|^github-actions$|^copilot)", re.I)


def is_bot_login(login):
    return bool(login) and bool(BOT_LOGIN_RE.search(login))


def owner_repo_of(path):
    try:
        p = subprocess.run(["git", "-C", path, "remote", "get-url", "origin"],
                            capture_output=True, text=True, timeout=10)
    except Exception:
        return None
    if p.returncode != 0:
        return None
    m = re.search(r"github\.com[:/]+([^/]+)/(.+?)(\.git)?$", p.stdout.strip())
    return f"{m.group(1)}/{m.group(2)}" if m else None


def gh(args, tries=5):
    """Run gh, return stdout text or None. Backs off on 403/429/5xx."""
    delay = 2
    err = None
    for _ in range(tries):
        p = subprocess.run(["gh"] + args, capture_output=True, text=True, timeout=120)
        if p.returncode == 0:
            return p.stdout
        err = p.stderr.strip()
        if re.search(r"\b(403|429|5\d\d)\b", err) or "rate limit" in err.lower() or "secondary rate" in err.lower():
            time.sleep(delay)
            delay = min(delay * 2, 60)
            continue
        print(f"  ! gh {' '.join(args[:3])} failed: {err[:300]}", file=sys.stderr)
        return None
    print(f"  ! gh {' '.join(args[:2])} kept failing: {err}", file=sys.stderr)
    return None


def gh_json(args, default=None):
    out = gh(args)
    if out is None:
        return default
    try:
        return json.loads(out)
    except json.JSONDecodeError:
        return default


def parse_ts(s):
    if not s:
        return None
    d = dt.datetime.fromisoformat(s.replace("Z", "+00:00"))
    return d if d.tzinfo else d.replace(tzinfo=dt.timezone.utc)


NOW = dt.datetime.now(dt.timezone.utc)

# Lightweight per-repo list: no commits/reviews/comments/body. A single `pr list`
# call requesting those nested connections across up to 2000 PRs multiplies out
# to more nodes than GitHub's GraphQL query-complexity cap allows (confirmed:
# "requesting up to 1,000,000 possible nodes ... exceeds ... 500,000") and the
# response either gets rejected outright or truncates mid-stream on a 502.
# Fetched per PR instead, below, where the same fields cost nothing to expand.
PR_FIELDS = ("number,title,author,isDraft,state,createdAt,mergedAt,closedAt,"
             "headRefName,baseRefName,additions,deletions,changedFiles,labels")

PR_DETAIL_FIELDS = "reviews,comments,body,commits"

RUN_FIELDS = "databaseId,name,event,headBranch,headSha,status,conclusion,createdAt,updatedAt,startedAt"
PR_LIMIT = 2000
RUN_LIMIT = 1000


def fetch_prs(owner_repo):
    """None when gh failed, so a failure is never read as a repo with no PRs."""
    return gh_json(["pr", "list", "--repo", owner_repo, "--state", "all",
                     "--limit", str(PR_LIMIT), "--json", PR_FIELDS], default=None)


def fetch_pr_detail(owner_repo, number):
    return gh_json(["pr", "view", str(number), "--repo", owner_repo, "--json", PR_DETAIL_FIELDS], default=None)


def fetch_runs(owner_repo):
    return gh_json(["run", "list", "--repo", owner_repo, "--limit", str(RUN_LIMIT),
                     "--json", RUN_FIELDS], default=None)


def json_pages(text):
    """Every page `gh api --paginate` printed, flattened. Depending on the gh version, array pages
    arrive merged into one array or back to back (`[...][...]`), which json.loads rejects."""
    dec, i, out = json.JSONDecoder(), 0, []
    while True:
        while i < len(text) and text[i].isspace():
            i += 1
        if i >= len(text):
            return out
        page, i = dec.raw_decode(text, i)
        out.extend(page if isinstance(page, list) else [page])


def fetch_timeline(owner_repo, number):
    """None when gh failed or its output would not parse."""
    out = gh(["api", "--paginate", f"repos/{owner_repo}/issues/{number}/timeline?per_page=100"])
    if out is None:
        return None
    try:
        events = json_pages(out)
    except json.JSONDecodeError:
        print(f"  ! timeline for {owner_repo}#{number} would not parse", file=sys.stderr)
        return None
    return [e for e in events if isinstance(e, dict) and e.get("event") in TIMELINE_EVENTS]


def fetch_timing(owner_repo, run_id):
    return gh_json(["api", f"repos/{owner_repo}/actions/runs/{run_id}/timing"], default=None)


def build(only=None):
    """only: repo names to refresh in place; every other repo's rows are kept."""
    t0 = time.time()
    api_calls = [0]
    skipped = []

    check_rate_limit()

    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    if os.path.exists(DB_PATH) and not only:
        os.remove(DB_PATH)
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()

    cur.executescript("""
    CREATE TABLE IF NOT EXISTS prs (
        repo TEXT, number INTEGER, title TEXT, author TEXT, author_is_bot INTEGER,
        state TEXT, is_draft INTEGER, created_ts TEXT, merged_ts TEXT, closed_ts TEXT,
        day TEXT, week TEXT, month TEXT,
        head_ref TEXT, base_ref TEXT, additions INTEGER, deletions INTEGER,
        changed_files INTEGER, commits INTEGER, review_count INTEGER, comment_count INTEGER,
        labels TEXT, body_redacted TEXT, hours_to_merge REAL, hours_open REAL,
        detail_ok INTEGER,
        PRIMARY KEY (repo, number)
    );
    CREATE TABLE IF NOT EXISTS pr_reviews (
        repo TEXT, number INTEGER, reviewer TEXT, reviewer_is_bot INTEGER,
        state TEXT, submitted_ts TEXT, body_redacted TEXT
    );
    CREATE TABLE IF NOT EXISTS pr_timeline (
        repo TEXT, number INTEGER, event TEXT, actor TEXT, ts TEXT
    );
    CREATE TABLE IF NOT EXISTS ci_runs (
        repo TEXT, run_id INTEGER, workflow_name TEXT, event TEXT, head_branch TEXT,
        head_sha TEXT, status TEXT, conclusion TEXT,
        created_ts TEXT, updated_ts TEXT, run_started_ts TEXT, duration_s REAL,
        day TEXT, week TEXT, month TEXT,
        PRIMARY KEY (repo, run_id)
    );
    CREATE TABLE IF NOT EXISTS ci_jobs (
        repo TEXT, run_id INTEGER, billable_ms INTEGER, run_duration_ms INTEGER
    );
    CREATE TABLE IF NOT EXISTS meta (source TEXT, path TEXT, rows INTEGER, extracted_at TEXT);
    """)

    # An --only refresh keeps the existing file, which may predate detail_ok; INSERTs are positional.
    if "detail_ok" not in {r[1] for r in cur.execute("PRAGMA table_info(prs)")}:
        cur.execute("ALTER TABLE prs ADD COLUMN detail_ok INTEGER")

    repo_map = {}  # repo name -> owner/repo
    for repo in (r for r in ALL_REPOS if not only or r in only):
        path = path_of(repo)
        if not os.path.isdir(path):
            skipped.append(f"{repo}: no checkout at {path}")
            continue
        owner_repo = owner_repo_of(path)
        if not owner_repo:
            skipped.append(f"{repo}: no GitHub remote")
            continue
        repo_map[repo] = owner_repo

    pr_counts, run_counts = {}, {}
    runs_ok = set()

    for repo, owner_repo in repo_map.items():
        prs = fetch_prs(owner_repo)
        api_calls[0] += 1
        if prs is None:
            skipped.append(f"{repo}: pr list failed; its PR rows are left as they were")
            prs = []
        else:
            if len(prs) >= PR_LIMIT:
                print(f"  ! {repo}: pr list returned its limit ({PR_LIMIT}); older PRs are missing", file=sys.stderr)
            for table in ("prs", "pr_reviews", "pr_timeline"):
                cur.execute(f"DELETE FROM {table} WHERE repo = ?", (repo,))
        pr_counts[repo] = len(prs)
        numbers = [pr["number"] for pr in prs]

        # Detail (reviews/comments/body/commits) and timeline are both per-PR
        # calls, fanned out together in one thread pool per repo.
        details, timelines = {}, {}
        if numbers:
            with ThreadPoolExecutor(max_workers=WORKERS) as ex:
                detail_futs = {ex.submit(fetch_pr_detail, owner_repo, n): n for n in numbers}
                timeline_futs = {ex.submit(fetch_timeline, owner_repo, n): n for n in numbers}
                for fut in as_completed(detail_futs):
                    n = detail_futs[fut]
                    api_calls[0] += 1
                    details[n] = fut.result()
                for fut in as_completed(timeline_futs):
                    n = timeline_futs[fut]
                    api_calls[0] += 1
                    timelines[n] = fut.result()

        n_detail_failed = sum(1 for v in details.values() if v is None)
        n_timeline_failed = sum(1 for v in timelines.values() if v is None)
        if n_detail_failed or n_timeline_failed:
            print(f"  ! {repo}: {n_detail_failed} PR details and {n_timeline_failed} timelines failed to fetch; "
                  f"their counts are NULL (detail_ok = 0) and their timeline events are missing", file=sys.stderr)

        pr_rows, review_rows, timeline_rows = [], [], []
        for pr in prs:
            n = pr["number"]
            detail_ok = details.get(n) is not None
            detail = details.get(n) or {}
            created = parse_ts(pr.get("createdAt"))
            merged = parse_ts(pr.get("mergedAt"))
            closed = parse_ts(pr.get("closedAt"))
            d = dims(created) if created else {"ts": None, "day": None, "week": None, "month": None}
            author = pr.get("author") or {}
            hours_to_merge = (merged - created).total_seconds() / 3600 if created and merged else None
            end = closed or merged or NOW
            hours_open = (end - created).total_seconds() / 3600 if created else None
            reviews = detail.get("reviews") or []
            comments = detail.get("comments") or []
            labels = ",".join(l.get("name", "") for l in (pr.get("labels") or []))
            body = detail.get("body")
            pr_rows.append((
                repo, n, pr.get("title"), author.get("login"), int(bool(author.get("is_bot"))),
                pr.get("state"), int(bool(pr.get("isDraft"))),
                d["ts"], merged.isoformat() if merged else None, closed.isoformat() if closed else None,
                d["day"], d["week"], d["month"],
                pr.get("headRefName"), pr.get("baseRefName"),
                pr.get("additions"), pr.get("deletions"), pr.get("changedFiles"),
                *((len(detail.get("commits") or []), len(reviews), len(comments)) if detail_ok else (None, None, None)),
                labels, redact(body)[:4000] if body else None,
                hours_to_merge, hours_open, int(detail_ok),
            ))
            for rv in reviews:
                rlogin = (rv.get("author") or {}).get("login")
                review_rows.append((
                    repo, n, rlogin, int(is_bot_login(rlogin)),
                    rv.get("state"), rv.get("submittedAt"),
                    redact(rv.get("body"))[:2000] if rv.get("body") else None,
                ))
            for e in timelines.get(n) or []:
                actor = (e.get("actor") or {}).get("login")
                timeline_rows.append((repo, n, e.get("event"), actor, e.get("created_at")))
        cur.executemany(
            "INSERT INTO prs VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", pr_rows)
        cur.executemany("INSERT INTO pr_reviews VALUES (?,?,?,?,?,?,?)", review_rows)
        cur.executemany("INSERT INTO pr_timeline VALUES (?,?,?,?,?)", timeline_rows)

        runs = fetch_runs(owner_repo)
        api_calls[0] += 1
        if runs is None:
            skipped.append(f"{repo}: run list failed; its CI rows are left as they were")
            runs = []
        else:
            if len(runs) >= RUN_LIMIT:
                print(f"  ! {repo}: run list returned its limit ({RUN_LIMIT}); older runs are missing", file=sys.stderr)
            for table in ("ci_runs", "ci_jobs"):
                cur.execute(f"DELETE FROM {table} WHERE repo = ?", (repo,))
            runs_ok.add(repo)
        run_counts[repo] = len(runs)
        run_rows = []
        for r in runs:
            created = parse_ts(r.get("createdAt"))
            updated = parse_ts(r.get("updatedAt"))
            started = parse_ts(r.get("startedAt"))
            duration = (updated - started).total_seconds() if started and updated and started.year > 1 else None
            d = dims(created) if created else {"ts": None, "day": None, "week": None, "month": None}
            run_rows.append((
                repo, r.get("databaseId"), r.get("name"), r.get("event"), r.get("headBranch"),
                r.get("headSha"), r.get("status"), r.get("conclusion"),
                d["ts"], updated.isoformat() if updated else None,
                started.isoformat() if started and started.year > 1 else None,
                duration, d["day"], d["week"], d["month"],
            ))
        cur.executemany("INSERT INTO ci_runs VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", run_rows)
        con.commit()
        print(f"  {repo}: {len(prs)} PRs, {len(timeline_rows)} timeline events, {len(runs)} runs", file=sys.stderr)

    # ci_jobs: billable minutes for at most the last TIMING_RUN_CAP runs per repo,
    # bounded to TIMING_BUDGET_S total so a slow API day can't stall the ingest.
    # This is the single heaviest fan-out (one call per run, up to
    # TIMING_RUN_CAP * len(repos)), so re-check quota before starting it.
    check_rate_limit()
    timing_start = time.time()
    timing_calls = 0
    job_rows = []
    timing_skipped = []
    cur.execute("SELECT repo, run_id FROM ci_runs ORDER BY repo, created_ts DESC")
    by_repo = {}
    for repo, run_id in cur.fetchall():
        by_repo.setdefault(repo, []).append(run_id)

    budget_hit = False
    for repo, run_ids in by_repo.items():
        # A repo whose run list failed kept its old ci_jobs; timing it again would duplicate them.
        if repo not in runs_ok:
            continue
        if budget_hit:
            timing_skipped.append(repo)
            continue
        owner_repo = repo_map[repo]
        targets = run_ids[:TIMING_RUN_CAP]
        with ThreadPoolExecutor(max_workers=WORKERS) as ex:
            futs = {ex.submit(fetch_timing, owner_repo, rid): rid for rid in targets}
            for fut in as_completed(futs):
                rid = futs[fut]
                timing_calls += 1
                res = fut.result()
                if res:
                    billable = sum(
                        j.get("total_ms", 0)
                        for j in (res.get("billable") or {}).values()
                    )
                    job_rows.append((repo, rid, billable, res.get("run_duration_ms")))
        if time.time() - timing_start > TIMING_BUDGET_S:
            budget_hit = True

    if job_rows:
        cur.executemany("INSERT INTO ci_jobs VALUES (?,?,?,?)", job_rows)
    if timing_skipped:
        skipped.append(f"ci_jobs: skipped timing for {timing_skipped} — {TIMING_BUDGET_S}s budget hit")
    api_calls[0] += timing_calls
    con.commit()

    extracted_at = dt.datetime.now(dt.timezone.utc).isoformat()
    for table in ("prs", "pr_reviews", "pr_timeline", "ci_runs", "ci_jobs"):
        n = cur.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        cur.execute("INSERT INTO meta VALUES (?,?,?,?)", (table, DB_PATH, n, extracted_at))
    con.commit()
    con.close()

    elapsed = time.time() - t0
    print("\n--- github.py summary ---")
    for table in ("prs", "pr_reviews", "pr_timeline", "ci_runs", "ci_jobs"):
        con2 = sqlite3.connect(DB_PATH)
        n = con2.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        con2.close()
        print(f"{table}: {n} rows")
    print("\nPer-repo PR / run counts:")
    for repo in repo_map:
        print(f"  {repo}: {pr_counts.get(repo, 0)} PRs, {run_counts.get(repo, 0)} runs")
    if skipped:
        print("\nSkipped:")
        for s in skipped:
            print(f"  - {s}")
    print(f"\napi_calls={api_calls[0]} elapsed_s={elapsed:.1f}")


if __name__ == "__main__":
    build(set(sys.argv[1:]) or None)
