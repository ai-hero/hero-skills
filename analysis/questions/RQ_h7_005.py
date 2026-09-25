"""Q4.04 / RQ-h7-005 -- Of the owner's corrective actions on agent work,
what share are approvals, steering, catching false claims, or scope
reverts, and how has that mix shifted? Haiku-backed (detectors/d_prompt_kind.py):
only regex-flagged prompts were ever classified -- the rest are
assumed non-corrective by construction of the flag itself, not because they
were checked and found clean.
"""
RQ_ID = "RQ-h7-005"
QUESTION = "Of the owner's corrective actions, what share are approvals, redirects, or corrections, and how has the mix shifted?"

SQL = """
SELECT substr(p.ts, 1, 7) AS month, pk.kind, COUNT(*) AS n
FROM detectors.prompt_kind_by_prompt p
JOIN detectors.prompt_kind pk ON pk.content_hash = p.content_hash
WHERE p.flagged = 1
GROUP BY month, pk.kind
ORDER BY month
"""


def answer(con):
    return con.execute(SQL).fetchall()


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(dict(row))
