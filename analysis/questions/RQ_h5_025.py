"""Q7.xx / RQ-h5-025 -- Are write-once knowledge records (archived plans,
feedback notes) ever read again? tool_calls has no file-path argument
(schema: session_id_hash, ts, tool, subagent_type, model_override, is_error,
was_rejected, question_count, skill_name), so a Read of a specific archived
file can't be distinguished from any other Read -- not answerable without
extending ingest/harness.py to capture the tool's path argument.
"""
RQ_ID = "RQ-h5-025"
QUESTION = "Are write-once knowledge records (archived plans, feedback notes) ever read again?"


def answer(con=None):
    return [{"answerable_by_code": False, "reason": "tool_calls has no file-path argument to match against"}]


if __name__ == "__main__":
    for row in answer():
        print(row)
