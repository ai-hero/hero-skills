"""Q19.xx / RQ-h7-015 -- Where do the agent's saved memories come from
(its own discovery, a human correction, a recorded decision)? This
repo's closest built classifier is d_prompt_kind.py, which labels
*prompts* (correction/redirect/approval/question/other), not memory
*entries* -- a memory file's own content would need its own Haiku pass
this repo has not built. The prompt-kind distribution is shown as
context for how much of the conversation stream is correction-shaped.
"""
RQ_ID = "RQ-h7-015"
QUESTION = "Where do the agent's saved memories come from: its own discovery, a human correction, or a recorded decision?"


def answer(con):
    kinds = con.execute(
        "SELECT kind, COUNT(*) AS n FROM detectors.prompt_kind GROUP BY kind ORDER BY n DESC"
    ).fetchall()
    return [{"prompt_kind_distribution_as_context": {r["kind"]: r["n"] for r in kinds}},
            {"answerable_by_code": False,
             "reason": "no classifier over memory-file *content* (vs. prompts) exists in this repo; "
                       "building one would need to read each fleet repo's memory directory and "
                       "label provenance per entry, which was not built here"}]


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
