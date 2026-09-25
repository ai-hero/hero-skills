"""Q3.02 / RQ-h6-046 -- What share of commits does each model co-author, and
does model choice correlate with commit type or follow-up fixes? D5-backed
follow-up rate, joined via commits.pr_number -> detectors.followups.
"""
RQ_ID = "RQ-h6-046"
QUESTION = "What share of commits does each model co-author, and does model choice correlate with follow-up fixes?"

SQL = """
SELECT c.trailer_model, c.conv_type,
       COUNT(*) AS commits,
       SUM(CASE WHEN f.followup_within_14d_days IS NOT NULL THEN 1 ELSE 0 END) AS followed_up,
       SUM(CASE WHEN f.repo IS NOT NULL THEN 1 ELSE 0 END) AS matched_to_a_pr
FROM git.commits c
LEFT JOIN detectors.followups f ON f.repo = c.repo AND f.number = c.pr_number
WHERE c.trailer_model IS NOT NULL
GROUP BY c.trailer_model, c.conv_type
ORDER BY commits DESC
"""


def answer(con):
    rows = con.execute(SQL).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        d["followup_rate_of_matched"] = round(d["followed_up"] / d["matched_to_a_pr"], 3) if d["matched_to_a_pr"] else None
        out.append(d)
    return out


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
