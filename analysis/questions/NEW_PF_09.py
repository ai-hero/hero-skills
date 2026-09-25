"""Q2.03 / NEW-PF-09 -- Does every data source cover the full study window
with timestamps, and where are its gaps? (Preflight) Checked directly per
source against the fleet's overall earliest/latest known activity.
"""
RQ_ID = "NEW-PF-09"
QUESTION = "Does every data source cover the full study window with timestamps, and where are its gaps?"

SOURCES = [
    ("git.commits", "committed_ts"), ("github.prs", "created_ts"),
    ("harness.sessions", "first_ts"), ("plans.plan_items", "created_ts"),
]


def answer(con):
    out = []
    for table, col in SOURCES:
        row = con.execute(f"SELECT MIN({col}), MAX({col}), COUNT(*) FROM {table} WHERE {col} IS NOT NULL").fetchone()
        out.append({"source": table, "earliest": row[0], "latest": row[1], "rows_with_ts": row[2]})
    return out


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
