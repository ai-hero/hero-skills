"""Preflight / NEW-A-12 -- Does each app repo have a design record?
D10-backed (detectors.presence, artifact='design_md', snapshot='head').
"""
RQ_ID = "NEW-A-12"
QUESTION = "Does each app repo have a design record?"

SQL = """
SELECT repo, role, present AS has_design_md
FROM detectors.presence
WHERE snapshot = 'head' AND artifact = 'design_md'
ORDER BY present, repo
"""


def answer(con):
    return con.execute(SQL).fetchall()


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(dict(row))
