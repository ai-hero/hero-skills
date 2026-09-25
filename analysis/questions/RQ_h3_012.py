"""Q11.xx / RQ-h3-012 -- How much of a repo's design record and agent
instructions has drifted false relative to the code? Same D2 drift signal
as the main table, reported per repo as a share.
"""
RQ_ID = "RQ-h3-012"
QUESTION = "How much of a repo's design record and agent instructions has drifted false relative to the code?"


def answer(con):
    rows = con.execute("SELECT repo, drifted_now FROM detectors.drift").fetchall()
    total = len(rows)
    drifted = sum(1 for r in rows if r["drifted_now"])
    return [{"repos_checked": total, "currently_drifted": drifted,
             "drifted_share": round(drifted / total, 3) if total else None}]


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
