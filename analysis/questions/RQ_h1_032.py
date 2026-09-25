"""Q9.xx / RQ-h1-032 -- Which gates catch a change's defects (pre-commit,
pre-push, automated self-review, CI, human review)? D8-backed. No pre-
commit/pre-push signal exists (see detectors/d8_gates.py) -- only CI and
review are countable.
"""
RQ_ID = "RQ-h1-032"
QUESTION = "Which gates catch a change's defects: CI, or human/bot review?"

SQL = "SELECT gate_kind, verdict, COUNT(*) AS n FROM detectors.gate_firings GROUP BY gate_kind, verdict ORDER BY n DESC"


def answer(con):
    return con.execute(SQL).fetchall()


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(dict(row))
