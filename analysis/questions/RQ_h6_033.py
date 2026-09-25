"""RQ-h6-033 -- bank row is empty (action: merge:NEW-C10-02); the bank
itself folded this question into NEW-C10-02. See that file.
"""
RQ_ID = "RQ-h6-033"
QUESTION = "(merged into NEW-C10-02 by the bank itself)"


def answer(con=None):
    return [{"merged_into": "NEW-C10-02"}]


if __name__ == "__main__":
    for row in answer():
        print(row)
