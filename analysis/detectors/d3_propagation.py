"""D3 propagation lag -> detectors.sqlite, table propagation.

Upstream sources: fleet.TEMPLATE_REPO (-> its clones, FLEET.md group: apps),
fleet.PLUGIN_REPO_NAME (-> every fleet repo, since it's the shared process
plugin), fleet.DESIGN_SYSTEM_REPO if configured (-> every app that imports
its registry -- approximated here as every fleet repo, since not every
app's package.json is ingested). Any of the three can be None/unset for a
fleet that has no template-and-clones shape, or no design system repo
declared in .analysis/config.json -- that upstream is just skipped, not
guessed. For each upstream commit,
downstream arrival is the earliest matching commit in a downstream repo,
matched in order:
  1. exact patch content: same normalized diff is out of scope (no patch-id
     table), so this uses exact SAME SUBJECT text (not normalized) as the
     strong signal -- a real cherry-pick or copy-paste fix keeps the exact
     message far more often than an independently-invented duplicate does.
  2. token Jaccard >= 0.8 between normalized subjects (ingest/git.py-style
     tokens), within 14 days.
A downstream repo with no match in either pass is "never arrived" (absent
from this table entirely, not a zero row -- a reader must check for the
downstream repo's absence, not filter on a null lag).

No control-check-flips-to-pass signal (pass 3 in the plan): check_results
only holds one compliance-sync snapshot per repo (see knowledge.py's known
gap), not a time series to detect a flip in.
"""
import os, re, sqlite3, sys, datetime as dt

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ingest.fleet import OUT, ALL_REPOS, GROUPS, TEMPLATE_REPO, PLUGIN_REPO_NAME, DESIGN_SYSTEM_REPO

DB_PATH = os.path.join(OUT, "detectors.sqlite")
GIT_DB = os.path.join(OUT, "git.sqlite")
WINDOW_DAYS = 14
JACCARD_THRESHOLD = 0.8

CONV_PREFIX = re.compile(r"^(feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert)(\([^)]*\))?!?:\s*", re.I)
NON_ALNUM = re.compile(r"[^a-z0-9 ]")


def tokens(subject):
    s = CONV_PREFIX.sub("", subject.lower())
    s = NON_ALNUM.sub(" ", s)
    return {t for t in s.split() if len(t) > 2}


def jaccard(a, b):
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def _parse(ts):
    return dt.datetime.fromisoformat(ts.replace("Z", "+00:00"))


CLONE_REPOS = sorted(r for r, g in GROUPS.items() if g == "apps")


def upstream_downstream_pairs():
    pairs = []
    if TEMPLATE_REPO:
        pairs += [(TEMPLATE_REPO, r) for r in CLONE_REPOS if r != TEMPLATE_REPO]
    pairs += [(PLUGIN_REPO_NAME, r) for r in ALL_REPOS if r != PLUGIN_REPO_NAME]
    if DESIGN_SYSTEM_REPO:
        pairs += [(DESIGN_SYSTEM_REPO, r) for r in ALL_REPOS if r not in (DESIGN_SYSTEM_REPO, PLUGIN_REPO_NAME)]
    return pairs


def build():
    con = sqlite3.connect(GIT_DB)
    commits = {}
    for repo, sha, subject, ts in con.execute(
        "SELECT repo, sha, subject, committed_ts FROM commits WHERE committed_ts IS NOT NULL"
    ).fetchall():
        commits.setdefault(repo, []).append((sha, subject, _parse(ts), tokens(subject)))
    con.close()
    for repo in commits:
        commits[repo].sort(key=lambda c: c[2])

    out = []
    for upstream_repo, downstream_repo in upstream_downstream_pairs():
        up_commits = commits.get(upstream_repo, [])
        down_commits = commits.get(downstream_repo, [])
        if not up_commits or not down_commits:
            continue
        for up_sha, up_subject, up_ts, up_tok in up_commits:
            window_end = up_ts + dt.timedelta(days=WINDOW_DAYS)
            best = None
            for down_sha, down_subject, down_ts, down_tok in down_commits:
                if down_ts <= up_ts or down_ts > window_end:
                    continue
                if down_subject == up_subject:
                    best = (down_sha, down_ts, "exact_subject")
                    break
                j = jaccard(up_tok, down_tok)
                if j >= JACCARD_THRESHOLD and best is None:
                    best = (down_sha, down_ts, f"jaccard_{j:.2f}")
            if best:
                down_sha, down_ts, method = best
                lag_hours = round((down_ts - up_ts).total_seconds() / 3600, 1)
                out.append((upstream_repo, up_sha, up_subject, downstream_repo, down_sha, method, lag_hours))

    outdb = sqlite3.connect(DB_PATH)
    outdb.execute("DROP TABLE IF EXISTS propagation")
    outdb.execute("""
        CREATE TABLE propagation (
            upstream_repo TEXT, upstream_sha TEXT, upstream_subject TEXT,
            downstream_repo TEXT, downstream_sha TEXT, match_method TEXT, lag_hours REAL
        )
    """)
    outdb.executemany("INSERT INTO propagation VALUES (?,?,?,?,?,?,?)", out)
    outdb.commit()
    print(f"detectors.sqlite: propagation {len(out)} matched arrivals across "
          f"{len(upstream_downstream_pairs())} upstream/downstream repo pairs")
    outdb.close()


if __name__ == "__main__":
    build()
