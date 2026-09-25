"""Q3.06 / RQ-h6-045 -- What share of sessions run in unattended (auto)
mode versus supervised confirmation, and does that share predict follow-up
fixes? No permission-mode field is captured anywhere in harness.sessions
or tool_calls -- not answerable without extending ingest/harness.py to
read the transcript's own permission-mode marker, if one is recorded.
"""
RQ_ID = "RQ-h6-045"
QUESTION = "What share of sessions run in unattended mode, and does that predict follow-up fixes?"


def answer(con=None):
    return [{"answerable_by_code": False, "reason": "no permission-mode field is captured by any ingest script"}]


if __name__ == "__main__":
    for row in answer():
        print(row)
