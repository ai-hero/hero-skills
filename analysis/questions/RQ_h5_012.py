"""Q14.xx / RQ-h5-012 -- How many of the register's checks have ever
failed or blocked something, by control?
"""
RQ_ID = "RQ-h5-012"
QUESTION = "How many of the register's checks have ever failed, by control?"

SQL = """
SELECT c.control_id, COUNT(DISTINCT c.check_id) AS total_checks,
       COUNT(DISTINCT CASE WHEN cr.result = '❌' THEN c.check_id END) AS ever_failed
FROM knowledge.checks c
LEFT JOIN knowledge.check_results cr ON cr.check_id = c.check_id
WHERE c.control_id IS NOT NULL AND c.control_id != ''
GROUP BY c.control_id
ORDER BY ever_failed DESC
"""


def answer(con):
    return con.execute(SQL).fetchall()[:20]


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(dict(row))
