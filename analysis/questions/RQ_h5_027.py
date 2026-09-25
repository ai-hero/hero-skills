"""Q7.xx / RQ-h5-027 -- Since the comment-quality rule was introduced, has
the rate of comments later removed as noise changed?
Proxy: commits whose subject or body mentions removing/trimming a comment
(regex match on "comment" plus a removal verb), by month, against the
rule's own introduction date (first skill_versions/doc_versions touch of
.claude/rules/comments.md).
"""
import re

RQ_ID = "RQ-h5-027"
QUESTION = "Since the comment-quality rule was introduced, has the rate of comments later removed as noise changed?"

REMOVE_COMMENT_RE = re.compile(r"comment", re.I)
REMOVE_VERB_RE = re.compile(r"\b(remove|drop|trim|delete|strip)\b", re.I)


def answer(con):
    rule_intro = con.execute(
        "SELECT MIN(updated_ts) FROM knowledge.instruction_files WHERE path LIKE '%comments.md%'"
    ).fetchone()[0]

    rows = con.execute("SELECT month, subject, body_redacted FROM git.commits WHERE month IS NOT NULL").fetchall()
    by_month = {}
    for r in rows:
        text = r["subject"] + " " + (r["body_redacted"] or "")
        if REMOVE_COMMENT_RE.search(text) and REMOVE_VERB_RE.search(text):
            by_month[r["month"]] = by_month.get(r["month"], 0) + 1

    return [{"comment_quality_rule_first_seen": rule_intro}] + \
           [{"month": m, "comment_removal_commits": n} for m, n in sorted(by_month.items())]


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
