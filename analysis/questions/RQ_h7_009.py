"""Q4.06 / RQ-h7-009 -- Does the owner's active time cluster on certain days
or hours, and does it grow in proportion to the fleet's size?

Hour/day distribution from prompts.ts directly. "Grows in proportion to
fleet size" needs a fleet-size-over-time series to compare against
(RQ-h1-015 has it) -- this reports active-time volume per week so that
comparison can be made by a reader, not joined here.
"""
RQ_ID = "RQ-h7-009"
QUESTION = "Does the owner's active time cluster on certain days or hours, and does it grow with the fleet?"

DOW_SQL = """
SELECT CAST(strftime('%w', ts) AS INTEGER) AS dow, CAST(strftime('%H', ts) AS INTEGER) AS hour_utc,
       COUNT(*) AS prompts
FROM harness.prompts
GROUP BY dow, hour_utc
ORDER BY dow, hour_utc
"""

WEEK_SQL = "SELECT week, COUNT(*) AS prompts, COUNT(DISTINCT day) AS active_days FROM harness.prompts GROUP BY week ORDER BY week"

DOW_NAMES = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]


def answer(con):
    by_hour = [{"day": DOW_NAMES[r["dow"]], "hour_utc": r["hour_utc"], "prompts": r["prompts"]}
               for r in con.execute(DOW_SQL).fetchall()]
    by_week = [dict(r) for r in con.execute(WEEK_SQL).fetchall()]
    return by_hour + by_week


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
