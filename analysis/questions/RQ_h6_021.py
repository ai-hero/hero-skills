"""RQ-h6-021 -- bank row is empty (action: merge:RQ-h6-020); the bank
itself folded this question into RQ-h6-020. See that file.
"""
RQ_ID = "RQ-h6-021"
QUESTION = "(merged into RQ-h6-020 by the bank itself)"


def answer(con=None):
    return [{"merged_into": "RQ-h6-020"}]


if __name__ == "__main__":
    for row in answer():
        print(row)
