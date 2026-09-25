"""D7 duplicate fixes -> detectors.sqlite, table duplicate_fixes.

The plan calls for token-Jaccard clustering of commit subjects and item
titles across repos within 7 days, excluding matches D3 (propagation lag)
already explains. D3 isn't built yet, so this is the simplified version:
commits are grouped by an exact normalized-subject signature (conventional-
commit prefix stripped, lowercased, punctuation removed, tokens sorted) --
a near-duplicate with reworded phrasing won't cluster here, so this
UNDER-counts duplication; it will not over-count. A cluster is only kept as
"duplicated" when it spans >= 2 different repos within a 7-day window --
same normalized subject in the SAME repo twice is not cross-repo
duplication (could be a genuine repeat fix, but that's D5's territory).
Once D3 exists, subtract its matches from this table's clusters to get the
plan's intended "no known upstream root" definition.
"""
import os, re, sqlite3, sys, datetime as dt

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ingest.fleet import OUT

DB_PATH = os.path.join(OUT, "detectors.sqlite")
GIT_DB = os.path.join(OUT, "git.sqlite")
WINDOW_DAYS = 7

CONV_PREFIX = re.compile(r"^(feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert)(\([^)]*\))?!?:\s*", re.I)
NON_ALNUM = re.compile(r"[^a-z0-9 ]")


def normalize(subject):
    s = CONV_PREFIX.sub("", subject.lower())
    s = NON_ALNUM.sub(" ", s)
    tokens = sorted(t for t in s.split() if len(t) > 2)
    return " ".join(tokens)


def _parse(ts):
    return dt.datetime.fromisoformat(ts.replace("Z", "+00:00"))


def build():
    con = sqlite3.connect(GIT_DB)
    rows = con.execute("SELECT repo, sha, subject, committed_ts FROM commits WHERE committed_ts IS NOT NULL").fetchall()
    con.close()

    by_sig = {}
    for repo, sha, subject, ts in rows:
        sig = normalize(subject)
        if not sig:
            continue
        by_sig.setdefault(sig, []).append((repo, sha, subject, _parse(ts)))

    clusters = []
    cluster_id = 0
    for sig, members in by_sig.items():
        members.sort(key=lambda m: m[3])
        used = set()
        for i, (repo, sha, subject, ts) in enumerate(members):
            if i in used:
                continue
            window = [m for j, m in enumerate(members[i:], start=i)
                      if (m[3] - ts).days <= WINDOW_DAYS]
            repos_in_window = {m[0] for m in window}
            if len(repos_in_window) < 2:
                continue
            cluster_id += 1
            for j, m in enumerate(members[i:], start=i):
                if m in window:
                    used.add(j)
            clusters.append((cluster_id, sig, window))

    out = []
    for cid, sig, window in clusters:
        for repo, sha, subject, ts in window:
            out.append((cid, sig, repo, sha, subject, ts.isoformat()))

    outdb = sqlite3.connect(DB_PATH)
    outdb.execute("DROP TABLE IF EXISTS duplicate_fixes")
    outdb.execute("""
        CREATE TABLE duplicate_fixes (
            cluster_id INTEGER, signature TEXT, repo TEXT, sha TEXT, subject TEXT, ts TEXT
        )
    """)
    outdb.executemany("INSERT INTO duplicate_fixes VALUES (?,?,?,?,?,?)", out)
    outdb.commit()
    print(f"detectors.sqlite: duplicate_fixes {len(clusters)} cross-repo clusters, {len(out)} commits involved")
    outdb.close()


if __name__ == "__main__":
    build()
