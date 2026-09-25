"""Q14.xx / RQ-h5-019 -- How many commits or work items reference a specific
control by id?

controls.control_id (e.g. C-SUPPLY, C-PRECOMMIT, C-GATES) is matched as a
whole word against commit subjects/bodies and plan-item titles -- a plain
substring match would also hit a control id as a prefix of another
(C-AUTH vs C-AUTHN), so this uses a word-boundary regex in Python rather
than SQL LIKE.
"""
import re

RQ_ID = "RQ-h5-019"
QUESTION = "How many commits or work items reference a specific control by id?"


def answer(con):
    control_ids = [r[0] for r in con.execute("SELECT DISTINCT control_id FROM knowledge.controls").fetchall()]
    commits = con.execute("SELECT subject, body_redacted FROM git.commits").fetchall()
    items = con.execute("SELECT title FROM plans.plan_items").fetchall()

    out = []
    for cid in sorted(control_ids):
        pattern = re.compile(r"\b" + re.escape(cid) + r"\b")
        commit_hits = sum(1 for subject, body in commits if pattern.search(subject) or pattern.search(body or ""))
        item_hits = sum(1 for (title,) in items if title and pattern.search(title))
        if commit_hits or item_hits:
            out.append({"control_id": cid, "commit_refs": commit_hits, "item_title_refs": item_hits})
    return out


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
