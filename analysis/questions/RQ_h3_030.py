"""Q11.xx / RQ-h3-030 -- How often does a security scanner report a
result that doesn't match reality? Same gap as RQ-h3-010: no execution-
trace or ground-truth signal exists to compare a scanner's verdict
against.
"""
RQ_ID = "RQ-h3-030"
QUESTION = "How often does a security scanner report a result that doesn't match reality?"


def answer(con=None):
    return [{"answerable_by_code": False,
             "reason": "no ground-truth signal exists to compare a scanner's reported verdict against"}]


if __name__ == "__main__":
    for row in answer():
        print(row)
