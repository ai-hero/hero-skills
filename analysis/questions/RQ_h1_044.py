"""Q2.07 / RQ-h1-044 -- How strictly did commit messages follow a convention
before the factory, and did the convention change once it arrived?

conv_type is set by ingest/git.py's CONV_RE (Conventional Commits: feat/fix/
docs/style/refactor/perf/test/build/ci/chore/revert). "Follows convention"
here means that regex matched the subject line -- a cheap proxy, not a
judgement on message quality. Merge commits are excluded: GitHub writes
their "Merge pull request #N" subject, not the author, and counting them
understates a repo's conventional share.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ingest.fleet import BASELINE_CUTOFF

RQ_ID = "RQ-h1-044"
QUESTION = "How strictly did commit messages follow a convention before vs after the factory?"

SQL = """
SELECT repo,
       CASE WHEN day < ? THEN 'before' ELSE 'after' END AS era,
       COUNT(*) AS commits,
       SUM(CASE WHEN conv_type IS NOT NULL THEN 1 ELSE 0 END) AS conventional,
       ROUND(SUM(CASE WHEN conv_type IS NOT NULL THEN 1 ELSE 0 END) * 1.0 / COUNT(*), 3) AS conventional_share,
       ROUND(AVG(LENGTH(subject)), 1) AS avg_subject_len
FROM v_commits
WHERE is_merge = 0
GROUP BY repo, era
ORDER BY repo, era
"""


def answer(con):
    return con.execute(SQL, (BASELINE_CUTOFF,)).fetchall()


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(dict(row))
