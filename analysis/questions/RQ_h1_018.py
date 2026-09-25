"""Q9.xx / RQ-h1-018 -- How deep and wide do chains of found work run: how
many new items does one item's discovery eventually spawn? D4-backed.
"""
RQ_ID = "RQ-h1-018"
QUESTION = "How deep and wide do chains of found work run?"

SQL = "SELECT root_repo, root_item_id, depth, root_fan_out FROM detectors.found_work"


def answer(con):
    rows = con.execute(SQL).fetchall()
    depths = sorted(r["depth"] for r in rows)
    roots = {}
    for r in rows:
        roots[(r["root_repo"], r["root_item_id"])] = r["root_fan_out"]
    fan_outs = sorted(roots.values())
    n, m = len(depths), len(fan_outs)
    return [{
        "found_work_edges": n, "distinct_roots": m,
        "max_depth": depths[-1] if n else None, "median_depth": depths[n // 2] if n else None,
        "max_fan_out": fan_outs[-1] if m else None, "median_fan_out": fan_outs[m // 2] if m else None,
    }]


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
