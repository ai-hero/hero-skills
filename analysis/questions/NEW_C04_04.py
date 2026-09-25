"""Q3.xx / NEW-C04-04 -- Are agent sessions run in sandboxes, and what
share of sessions use one? No sandbox/isolation flag is captured by
ingest/harness.py (tool_calls has no such column) -- not answerable without
extending the ingest to read it from the transcript, if the transcript
records it at all.
"""
RQ_ID = "NEW-C04-04"
QUESTION = "Are agent sessions run in sandboxes, and what share of sessions use one?"


def answer(con=None):
    return [{"answerable_by_code": False, "reason": "no sandbox/isolation flag is captured by any ingest script"}]


if __name__ == "__main__":
    for row in answer():
        print(row)
