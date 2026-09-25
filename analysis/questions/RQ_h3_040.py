"""Q11.xx / RQ-h3-040 -- Was each code-execution vector in the process
plugin closed by removing the mechanism or by guarding it? Proxy: plugin
commits whose subject mentions security/vulnerability/exploit/injection,
classified by whether the subject also says remove/delete (closed) vs
guard/validate/sanitize/restrict (guarded).
"""
import os, re, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ingest.fleet import PLUGIN_REPO_NAME

RQ_ID = "RQ-h3-040"
QUESTION = "Was each code-execution vector in the process plugin closed by removing the mechanism, or by guarding it?"

VECTOR_RE = re.compile(r"vulnerab|exploit|injection|spoof|subvert|security", re.I)
REMOVE_RE = re.compile(r"\b(remove|delete|drop)\b", re.I)
GUARD_RE = re.compile(r"\b(guard|validate|sanitize|restrict|escape)\b", re.I)


def answer(con):
    rows = con.execute(
        "SELECT sha, subject, body_redacted FROM git.commits WHERE repo = ?", (PLUGIN_REPO_NAME,)
    ).fetchall()
    removed = guarded = other = 0
    hits = []
    for r in rows:
        text = r["subject"] + " " + (r["body_redacted"] or "")
        if not VECTOR_RE.search(text):
            continue
        if REMOVE_RE.search(text):
            removed += 1
        elif GUARD_RE.search(text):
            guarded += 1
        else:
            other += 1
        hits.append(r["subject"])
    return [{"security_shaped_commits": len(hits), "closed_by_removal": removed,
             "closed_by_guarding": guarded, "unclear": other}]


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
