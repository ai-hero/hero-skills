"""Q15.xx / RQ-cicd-005 -- When the process plugin changes a shared CI
workflow, how many consumer repos need a follow-up fix? D3+D8: propagation
arrivals from the plugin repo whose PR later needed a D5 follow-up, same
chain as NEW-C10-03, scoped by relevance to CI workflow paths.
"""
RQ_ID = "RQ-cicd-005"
QUESTION = "When the process plugin changes a shared CI workflow, how many consumer repos need a follow-up fix?"


def answer(con):
    from questions.NEW_C10_03 import answer as base_answer
    rows = base_answer(con)
    return [rows[0]] if rows else rows


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
