"""Q12.xx / NEW-C12-01 -- Does the factory record every point where it
waits on the human (questions asked, ready-marks, go-authorizations,
approvals) with a timestamp for the ask and for the answer? D6+D10
combined: asks have both ends timestamped (asks.ts + the matched next
prompt); ready-marks have ready_ts but no explicit "answer" event separate
from the field itself; go-authorizations (wayfare-start-goal invocations)
have only the ask side, no distinct answer timestamp.
"""
RQ_ID = "NEW-C12-01"
QUESTION = "Does the factory record every point where it waits on the human, with timestamps for both ends?"


def answer(con):
    asks = con.execute("SELECT COUNT(*) FROM harness.asks WHERE ts IS NOT NULL").fetchone()[0]
    ready_marks = con.execute("SELECT COUNT(*) FROM plans.plan_items WHERE ready_ts IS NOT NULL").fetchone()[0]
    go_events = con.execute(
        "SELECT COUNT(*) FROM harness.tool_calls WHERE skill_name LIKE '%wayfare-start-goal%'"
    ).fetchone()[0]
    return [{
        "asks_with_a_timestamp": asks, "asks_have_an_answer_event": "yes (the next prompt)",
        "ready_marks_with_a_timestamp": ready_marks, "ready_marks_have_a_separate_answer_event": False,
        "go_authorizations_recorded": go_events, "go_authorizations_have_a_separate_ask_timestamp": False,
    }]


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
