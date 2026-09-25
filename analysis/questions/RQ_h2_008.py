"""Q16.xx / RQ-h2-008 -- How well does the number of PRs planned for a
goal predict the number it actually takes? No "planned PR count" field
exists on goals (plan_items has budget/budget_max for TASK items, not a
PR estimate) -- not answerable as asked.
"""
RQ_ID = "RQ-h2-008"
QUESTION = "How well does the number of PRs planned for a goal predict the number it actually takes?"


def answer(con=None):
    return [{"answerable_by_code": False,
             "reason": "no planned-PR-count field exists on goals; budget/budget_max apply to task items, not PRs"}]


if __name__ == "__main__":
    for row in answer():
        print(row)
