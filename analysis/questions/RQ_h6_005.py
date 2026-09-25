"""Q10.xx / RQ-h6-005 -- Does a repo's design-record size track its
architectural complexity, or just its age and churn?
Complexity proxy: total insertions (a repo's cumulative code churn) -- a
rough stand-in, since true architectural complexity (module count, coupling)
isn't in any ingested table. Age from git.repos.first_commit_ts.
"""
RQ_ID = "RQ-h6-005"
QUESTION = "Does a repo's design-record size track its architectural complexity, age, or churn?"

SQL = """
SELECT r.repo, r.first_commit_ts,
       (SELECT SUM(insertions) FROM git.commits c WHERE c.repo = r.repo) AS total_insertions,
       (SELECT MAX(bytes) FROM knowledge.doc_versions d WHERE d.repo = r.repo AND d.doc = 'DESIGN.md') AS design_md_bytes
FROM git.repos r
WHERE r.role NOT IN ('design source')
"""


def answer(con):
    import datetime as dt
    rows = con.execute(SQL).fetchall()
    out = []
    for r in rows:
        if r["design_md_bytes"] is None:
            continue
        age_days = (dt.datetime.now(dt.timezone.utc) - dt.datetime.fromisoformat(r["first_commit_ts"])).days
        out.append({
            "repo": r["repo"], "age_days": age_days,
            "total_insertions": r["total_insertions"], "design_md_bytes": r["design_md_bytes"],
            "bytes_per_1k_insertions": round(r["design_md_bytes"] / max(1, r["total_insertions"] / 1000), 1),
        })
    return sorted(out, key=lambda x: -x["design_md_bytes"])


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
