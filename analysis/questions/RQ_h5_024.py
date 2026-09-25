"""Q7.xx / RQ-h5-024 -- Does standing documentation (agent instructions,
design records) keep growing with repo age, or does it plateau?

Each row is one repo's most-recent doc_versions snapshot (the last commit
that touched DESIGN.md/AGENTS.md/etc), reported against that repo's age in
days at the snapshot date (git.repos.first_commit_ts) -- a cross-sectional
"size vs age" view, not a per-repo time series (RQ-h6-027 covers the plugin's
own growth curve over time already).
"""
RQ_ID = "RQ-h5-024"
QUESTION = "Does standing documentation keep growing with repo age, or plateau?"

SQL = """
SELECT d.repo, d.doc, d.bytes, d.lines, d.sections, d.ts,
       r.first_commit_ts,
       CAST(julianday(d.ts) - julianday(r.first_commit_ts) AS INTEGER) AS repo_age_days
FROM knowledge.doc_versions d
JOIN git.repos r ON r.repo = d.repo
WHERE d.ts = (
    SELECT MAX(d2.ts) FROM knowledge.doc_versions d2 WHERE d2.repo = d.repo AND d2.doc = d.doc
)
ORDER BY d.doc, repo_age_days
"""


def answer(con):
    return con.execute(SQL).fetchall()


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(dict(row))
