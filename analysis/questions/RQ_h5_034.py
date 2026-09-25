"""Q7.xx / RQ-h5-034 -- Do work items with more verification log entries
have fewer later mistake entries?
"""
RQ_ID = "RQ-h5-034"
QUESTION = "Do work items with more verification log entries have fewer later mistake entries?"

SQL = """
SELECT repo, item_id,
       SUM(CASE WHEN kind = 'verify' THEN 1 ELSE 0 END) AS verify_entries,
       SUM(CASE WHEN kind = 'mistake' THEN 1 ELSE 0 END) AS mistake_entries
FROM plans.item_logs
GROUP BY repo, item_id
HAVING verify_entries > 0 OR mistake_entries > 0
"""


def answer(con):
    rows = con.execute(SQL).fetchall()
    buckets = {"0 verify": [], "1 verify": [], "2+ verify": []}
    for r in rows:
        key = "0 verify" if r["verify_entries"] == 0 else "1 verify" if r["verify_entries"] == 1 else "2+ verify"
        buckets[key].append(r["mistake_entries"])
    return [{"bucket": k, "items": len(v), "avg_mistake_entries": round(sum(v) / len(v), 2) if v else None}
            for k, v in buckets.items()]


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
