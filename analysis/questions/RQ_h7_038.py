"""Q4.xx / RQ-h7-038 -- How did the owner's interaction with the harness
change over the study (prompt length, slash-command share, correction
rate)? Combines RQ-h6-029's prompt-length/slash-share trend with the
Haiku-classified correction rate per month.
"""
RQ_ID = "RQ-h7-038"
QUESTION = "How did the owner's interaction with the harness change over the study?"

BASE_SQL = """
SELECT month, COUNT(*) AS prompts, ROUND(AVG(chars), 1) AS avg_chars,
       ROUND(SUM(is_slash_command) * 1.0 / COUNT(*), 3) AS slash_share
FROM harness.prompts WHERE month IS NOT NULL GROUP BY month
"""

CORRECTION_SQL = """
SELECT substr(p.ts, 1, 7) AS month, COUNT(*) AS corrections
FROM detectors.prompt_kind_by_prompt p
JOIN detectors.prompt_kind pk ON pk.content_hash = p.content_hash
WHERE p.flagged = 1 AND pk.kind IN ('correction', 'redirect')
GROUP BY month
"""


def answer(con):
    base = {r["month"]: dict(r) for r in con.execute(BASE_SQL).fetchall()}
    corrections = {r["month"]: r["corrections"] for r in con.execute(CORRECTION_SQL).fetchall()}
    out = []
    for month, b in sorted(base.items()):
        c = corrections.get(month, 0)
        out.append({**b, "steering_prompts": c, "steering_share": round(c / b["prompts"], 4)})
    return out


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
