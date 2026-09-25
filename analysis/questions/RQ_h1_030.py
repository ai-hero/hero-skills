"""Q9.xx / RQ-h1-030 -- What is the distribution of a merged PR's wall
time (open to merge)?
"""
RQ_ID = "RQ-h1-030"
QUESTION = "What is the distribution of a merged PR's wall time (open to merge)?"

SQL = "SELECT hours_to_merge FROM github.prs WHERE hours_to_merge IS NOT NULL"


def answer(con):
    hours = sorted(r[0] for r in con.execute(SQL).fetchall())
    n = len(hours)
    if not n:
        return [{"note": "no PRs with hours_to_merge"}]
    return [{
        "merged_prs": n, "p10_hours": round(hours[int(n * 0.1)], 1), "median_hours": round(hours[n // 2], 1),
        "p90_hours": round(hours[int(n * 0.9)], 1), "max_hours": round(hours[-1], 1),
    }]


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
