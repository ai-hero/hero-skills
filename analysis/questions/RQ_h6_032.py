"""Q17.xx / RQ-h6-032 -- When one skill's output feeds the next, how
often does the next skill use it directly rather than redoing the
work? No chain-of-skill-invocation log with per-step inputs/outputs is
ingested by this repo (sessions are tracked at the repo/spend level,
not at the skill-call level), so this needs a transcript-level Haiku
pass this repo has not built.
"""
RQ_ID = "RQ-h6-032"
QUESTION = "When one skill's output feeds the next, how often does the next skill use it directly rather than redoing the work?"


def answer(con):
    return [{"answerable_by_code": False,
             "reason": "no per-skill-invocation input/output log is ingested here; only repo-level "
                       "spend and gate/propagation events are tracked, none of which record whether "
                       "one skill's output was reused vs recomputed by the next"}]


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
