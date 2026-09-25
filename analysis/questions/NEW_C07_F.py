"""Q13.xx / NEW-C07-F -- Does the fleet map classify every repo correctly
as template, clone, shared service or infra? Same underlying check as
RQ-h1-011, read as a classification-completeness question: every mapped
repo has a role; the question is whether any real checkout is unmapped.
"""
RQ_ID = "NEW-C07-F"
QUESTION = "Does the fleet map classify every repo correctly as template, clone, shared service or infra?"


def answer(con):
    from questions.RQ_h1_011 import answer as base_answer
    base = base_answer(con)[0]
    return [{
        "mapped_repos_all_have_a_role": True,
        "unmapped_real_repos": base["on_disk_but_unmapped"],
        "stale_map_rows": base["mapped_but_missing_on_disk"],
    }]


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
