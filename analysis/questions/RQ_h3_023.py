"""Q11.xx / RQ-h3-023 -- Within the process plugin's own history, what
share of changes repair its own earlier mistakes?
Proxy: the plugin repo's commits whose conv_type is 'fix' or subject
mentions bug/mistake/regression, as a share of all its commits.
"""
import os, re, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ingest.fleet import PLUGIN_REPO_NAME

RQ_ID = "RQ-h3-023"
QUESTION = "Within the process plugin's own history, what share of changes repair its own earlier mistakes?"

MISTAKE_RE = re.compile(r"\b(bug|mistake|regression|broken|fix(es|ed)?)\b", re.I)


def answer(con):
    rows = con.execute(
        "SELECT conv_type, subject FROM git.commits WHERE repo = ?", (PLUGIN_REPO_NAME,)
    ).fetchall()
    total = len(rows)
    repairs = sum(1 for r in rows if r["conv_type"] == "fix" or MISTAKE_RE.search(r["subject"]))
    return [{"plugin_repo": PLUGIN_REPO_NAME, "plugin_commits": total, "repair_like_commits": repairs,
             "repair_share": round(repairs / total, 3) if total else None}]


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
