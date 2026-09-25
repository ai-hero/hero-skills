"""Q13.xx / RQ-h4-023 -- How many dated decisions do the fleet's design
records hold, and do entries get shorter or longer over time?

design_decisions.date_in_text is the date written IN the decision heading
(e.g. "2026-07-14 -- One container..."), not when the doc was committed --
that's the right axis for "does the record itself compress over time," so
this buckets by that date's month, not first_seen_ts's month.

text_redacted is truncated to 1500 chars at ingest (ingest/knowledge.py
line ~198), so LENGTH() is right-censored there: a month whose entries hit
that cap looks the same length whether the real entries are 1500 or 4000
chars. avg/max_chars below are only trustworthy for growth below 1500 --
for a month at max_chars=1500, "entries get longer" is unconfirmed, not
refuted.
"""
RQ_ID = "RQ-h4-023"
QUESTION = "How many dated decisions do the design records hold, and do entries get shorter or longer over time?"

SQL = """
SELECT substr(date_in_text, 1, 7) AS month,
       COUNT(*) AS decisions,
       ROUND(AVG(LENGTH(text_redacted)), 0) AS avg_chars,
       MIN(LENGTH(text_redacted)) AS min_chars,
       MAX(LENGTH(text_redacted)) AS max_chars
FROM knowledge.design_decisions
WHERE date_in_text IS NOT NULL
GROUP BY month
ORDER BY month
"""


def answer(con):
    return con.execute(SQL).fetchall()


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(dict(row))
