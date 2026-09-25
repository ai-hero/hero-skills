"""Q12.xx / RQ-h1-001 -- At which template version was each clone
created, and how far has each clone drifted from that starting point?
Template "version" proxy: template commit count as of the clone's founding
date (from RQ-h1-011/NEW-A-09's template_age data, reframed as commit
count rather than days). Drift-since: D1 change-set count in the clone
since founding, as a rough "how much has moved" proxy.
"""
RQ_ID = "RQ-h1-001"
QUESTION = "At which template version was each clone created, and how far has it drifted since?"


def answer(con):
    import os, sys, datetime as dt
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from ingest.fleet import TEMPLATE_REPO
    if not TEMPLATE_REPO:
        return [{"note": "no FLEET.md group: template repo in this fleet"}]
    clones = con.execute("SELECT repo, first_commit_ts FROM git.repos WHERE role = 'clone'").fetchall()
    out = []
    for r in clones:
        template_commits_at_founding = con.execute(
            "SELECT COUNT(*) FROM git.commits WHERE repo = ? AND committed_ts <= ?",
            (TEMPLATE_REPO, r["first_commit_ts"]),
        ).fetchone()[0]
        clone_commits_since = con.execute(
            "SELECT COUNT(*) FROM git.commits WHERE repo = ?", (r["repo"],)
        ).fetchone()[0]
        out.append({"repo": r["repo"], "template_commits_at_founding": template_commits_at_founding,
                    "clone_commits_since_founding": clone_commits_since})
    return out


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
