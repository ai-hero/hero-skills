"""Q3.13-ish / NEW-C04-01 -- Does the harness record session limits and
outages, per session and per account? limit_events carries session_id_hash
and org (account) columns; reports how many rows populate each.
"""
RQ_ID = "NEW-C04-01"
QUESTION = "Does the harness record session limits and outages, per session and per account?"


def answer(con):
    row = con.execute(
        "SELECT COUNT(*) AS n, COUNT(DISTINCT session_id_hash) AS sessions, COUNT(DISTINCT org) AS orgs "
        "FROM harness.limit_events"
    ).fetchone()
    return [{"limit_events": row["n"], "distinct_sessions": row["sessions"], "distinct_orgs": row["orgs"]}]


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
