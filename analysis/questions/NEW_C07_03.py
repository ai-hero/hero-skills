"""Q13.xx / NEW-C07-03 -- Does the factory have a cross-repo message
channel that supports both broadcast and targeted messages? plans.messages
schema (from_repo, to_repo, direction): each message names one from/to pair,
and the schema has no broadcast marker.
"""
RQ_ID = "NEW-C07-03"
QUESTION = "Does the factory have a cross-repo message channel that supports both broadcast and targeted messages?"


def answer(con):
    rows = con.execute("SELECT from_repo, to_repo FROM plans.messages").fetchall()
    if not rows:
        return [{"note": "no messages recorded"}]
    return [{"messages": len(rows), "all_targeted_point_to_point": True,
             "note": "schema has from_repo/to_repo per message, no broadcast/all-repos marker -- "
                     "the channel as recorded is targeted only"}]


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
