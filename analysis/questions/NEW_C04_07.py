"""Q3.xx / NEW-C04-07 -- Does each repo have a pre-commit and a pre-push
hook, and a CI workflow? D10-backed.
"""
RQ_ID = "NEW-C04-07"
QUESTION = "Does each repo have a pre-commit and a pre-push hook, and a CI workflow?"


def answer(con):
    rows = con.execute(
        "SELECT repo, artifact, present FROM detectors.presence "
        "WHERE snapshot='head' AND artifact IN ('pre_commit_config', 'github_workflows')"
    ).fetchall()
    by_repo = {}
    for r in rows:
        by_repo.setdefault(r["repo"], {})[r["artifact"]] = r["present"]
    return [{"repo": repo, **v} for repo, v in sorted(by_repo.items())]


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
