"""Q11.xx / NEW-C06-01 -- Are secret scanning, dependency scanning and
container scanning on in every repo? knowledge.check_results joined to
checks whose control_id is C-SECRETS (or title/check_id mentions scan).
"""
RQ_ID = "NEW-C06-01"
QUESTION = "Are secret scanning, dependency scanning and container scanning on in every repo?"

SQL = """
SELECT DISTINCT cr.repo, c.control_id, c.check_id, cr.result, cr.as_of
FROM knowledge.check_results cr
JOIN knowledge.checks c ON c.check_id = cr.check_id
WHERE c.control_id = 'C-SECRETS' OR c.check_id LIKE '%SCAN%' OR c.check_id LIKE '%SECRET%'
ORDER BY cr.repo
"""


def answer(con):
    return con.execute(SQL).fetchall()


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(dict(row))
