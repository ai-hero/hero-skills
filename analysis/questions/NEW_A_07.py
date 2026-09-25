"""Q1.xx / NEW-A-07 -- How has what the automated reviewer and the
approver check changed over the factory's life? sql half: gate_kind
distribution by month from gate_firings. Reading *what* each gate kind
actually checks over time (its rule content, not just its firing) needs
a human diff of the gate configs, or a Haiku pass over commit history
to those configs.
"""
RQ_ID = "NEW-A-07"
QUESTION = "How has what the automated reviewer and the approver check changed over the factory's life?"


def answer(con):
    rows = con.execute(
        "SELECT strftime('%Y-%m', ts) AS month, gate_kind, COUNT(*) AS n "
        "FROM detectors.gate_firings GROUP BY 1, 2 ORDER BY 1"
    ).fetchall()
    by_month = {}
    for r in rows:
        by_month.setdefault(r["month"], {})[r["gate_kind"]] = r["n"]
    return [{"month": m, **counts} for m, counts in sorted(by_month.items())] + [
        {"answerable_by_code": "partial",
         "reason": "gate *firing volume* by kind and month is above; what each gate's checks "
                   "actually cover, and how that ruleset changed, needs a human or Haiku diff of "
                   "the gate configs themselves, not built here"}
    ]


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
