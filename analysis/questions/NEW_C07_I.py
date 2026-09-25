"""Q13.xx / NEW-C07-I -- Does a breaking upstream change record which
downstream repos it affects? Proxy: a process-plugin or template commit
whose body mentions another fleet repo by name.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ingest.fleet import ALL_REPOS, TEMPLATE_REPO, PLUGIN_REPO_NAME

RQ_ID = "NEW-C07-I"
QUESTION = "Does a breaking upstream change record which downstream repos it affects?"


def answer(con):
    upstreams = [r for r in (PLUGIN_REPO_NAME, TEMPLATE_REPO) if r]
    if not upstreams:
        return [{"note": "no process plugin or template repo identified for this fleet"}]
    rows = con.execute(
        f"SELECT sha, subject, body_redacted FROM git.commits WHERE repo IN "
        f"({','.join('?' * len(upstreams))}) AND (subject LIKE '%break%' OR body_redacted LIKE '%break%')",
        upstreams,
    ).fetchall()
    other_repos = [r for r in ALL_REPOS if r not in upstreams]
    named = 0
    for r in rows:
        text = r["subject"] + " " + (r["body_redacted"] or "")
        if any(repo in text for repo in other_repos):
            named += 1
    return [{"breaking_change_commits": len(rows), "naming_an_affected_downstream_repo": named}]


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
