"""Q11.xx / RQ-h3-034 -- Has anyone tested whether the automated approval
judge can be subverted by a fabricated PR description or a misleading
diff? Proxy: plan_items/commits whose title/subject mentions the judge
and a subversion-shaped word (spoof, fake, fabricat, subvert, bypass,
trick, mislead).
"""
import re

RQ_ID = "RQ-h3-034"
QUESTION = "Has anyone tested whether the automated approval judge can be subverted?"

SUBVERT_RE = re.compile(r"spoof|fake|fabricat|subvert|bypass|trick|mislead", re.I)
JUDGE_RE = re.compile(r"judge|auto.?approve", re.I)


def answer(con):
    items = con.execute(
        "SELECT repo, item_id, title FROM plans.plan_items WHERE title IS NOT NULL"
    ).fetchall()
    hits = [dict(r) for r in items if JUDGE_RE.search(r["title"]) and SUBVERT_RE.search(r["title"])]
    commits = con.execute(
        "SELECT repo, sha, subject FROM git.commits WHERE subject IS NOT NULL"
    ).fetchall()
    commit_hits = [dict(r) for r in commits if JUDGE_RE.search(r["subject"]) and SUBVERT_RE.search(r["subject"])]
    return [{"matching_items": len(hits), "matching_commits": len(commit_hits)}] + hits + commit_hits


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
