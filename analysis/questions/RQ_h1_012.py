"""Q12.xx / RQ-h1-012 -- What does a new clone inherit from the template
on day one: ignore files, environment config, CI, hardening? D10-backed:
every artifact's presence at each clone's first_commit snapshot.
"""
RQ_ID = "RQ-h1-012"
QUESTION = "What does a new clone inherit from the template on day one?"

SQL = """
SELECT p.repo, p.artifact, p.present FROM detectors.presence p
JOIN git.repos r ON r.repo = p.repo
WHERE p.snapshot = 'first_commit' AND r.role = 'clone'
"""


def answer(con):
    rows = con.execute(SQL).fetchall()
    by_repo = {}
    for r in rows:
        by_repo.setdefault(r["repo"], {})[r["artifact"]] = r["present"]
    return [{"repo": repo, **v} for repo, v in sorted(by_repo.items())]


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
