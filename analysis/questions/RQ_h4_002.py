"""Q13.xx / RQ-h4-002 -- Once a cross-repo message is delivered, how long
until the receiving repo answers? messages has one created_ts per message,
not a separate delivered/answered pair -- a "reply" is its own message row
(direction/subject referencing the original), so this pairs an "answered"
message to its likely original by matching subject text, the closest
available signal.
"""
RQ_ID = "RQ-h4-002"
QUESTION = "Once a cross-repo message is delivered, how long until the receiving repo answers?"


def answer(con):
    rows = con.execute("SELECT from_repo, to_repo, created_ts, status, subject FROM plans.messages").fetchall()
    replies = [r for r in rows if r["subject"] and r["subject"].startswith("[reply]")]
    asks = [r for r in rows if r["subject"] and r["subject"].startswith("[ask]")]
    return [{"messages": len(rows), "asks": len(asks), "replies": len(replies),
             "note": "no explicit ask<->reply id link exists to compute a lag; counts only"}]


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
