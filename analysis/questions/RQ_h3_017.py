"""Q11.xx / RQ-h3-017 -- When a shared component or repo is renamed, how
many dependents break because they still reference the old name? Proxy:
after a repo rename (fleet.REPO_ALIASES, or FLEET.md's mapped-but-missing
row), commits elsewhere mentioning the OLD name within 30 days.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ingest.fleet import REPO_ALIASES

RQ_ID = "RQ-h3-017"
QUESTION = "When a shared component or repo is renamed, how many dependents break because they still reference the old name?"


def answer(con):
    if not REPO_ALIASES:
        return [{"note": "no repo_aliases configured in .analysis/config.json for this fleet"}]
    out = []
    for old_name, new_name in REPO_ALIASES.items():
        rows = con.execute(
            "SELECT repo, COUNT(*) AS n FROM git.commits WHERE repo != ? AND "
            "(subject LIKE ? OR body_redacted LIKE ?) GROUP BY repo",
            (new_name, f"%{old_name}%", f"%{old_name}%"),
        ).fetchall()
        out.append({"old_name": old_name, "new_name": new_name,
                    "other_repos_still_mentioning_old_name": len(rows)})
    return out


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
