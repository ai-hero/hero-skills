"""Q9.xx / RQ-h1-038 -- How often is a repo's design record updated in the
same change (commit) as the architectural code it describes?
Proxy: a commit that touches DESIGN.md AND touches a non-doc file in the
same commit (commit_files has both an entry with path='DESIGN.md' and
other entries).
"""
RQ_ID = "RQ-h1-038"
QUESTION = "How often is a repo's design record updated in the same change as the architecture it describes?"

SQL = """
SELECT repo, sha, GROUP_CONCAT(path) AS paths
FROM git.commit_files
WHERE sha IN (SELECT DISTINCT sha FROM git.commit_files WHERE path = 'DESIGN.md')
GROUP BY repo, sha
"""


def answer(con):
    rows = con.execute(SQL).fetchall()
    total = len(rows)
    with_other_files = sum(1 for r in rows if len(r["paths"].split(",")) > 1)
    return [{"commits_touching_design_md": total,
             "also_touched_other_files_same_commit": with_other_files,
             "share": round(with_other_files / total, 3) if total else None}]


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
