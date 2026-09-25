"""Q14.xx / NEW-C08-B -- Is register drift caught by an automated check or
only by a manual audit? Proxy: register_history's own git-log-derived
timestamps are all commit events (someone/something committed CONTROLS.yaml/
CHECKS.yaml), which is itself the answer -- there's no separate "automated
detector fired" event distinct from "a sync ran and committed the result."
"""
RQ_ID = "NEW-C08-B"
QUESTION = "Is register drift caught by an automated check or only by a manual audit?"


def answer(con):
    n = con.execute("SELECT COUNT(DISTINCT sha) FROM knowledge.register_history").fetchone()[0]
    return [{
        "register_sync_commits": n,
        "note": "no distinct 'automated detector fired outside a sync' event exists in the data -- "
                "every register_history row is a sync commit, so this can't separate automated "
                "continuous detection from a manual/scheduled audit run",
    }]


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
