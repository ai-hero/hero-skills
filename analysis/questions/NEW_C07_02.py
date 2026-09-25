"""Q13.xx / NEW-C07-02 -- Of changes that end up fleet-wide, what share
were made upstream first (template/plugin) versus starting in a clone and
spreading sideways? Same D7 cluster data as RQ-h6-002, reframed as a share.
"""
RQ_ID = "NEW-C07-02"
QUESTION = "Of changes that end up fleet-wide, what share started upstream versus spreading sideways from a clone?"


def answer(con):
    from questions.RQ_h6_002 import answer as base_answer
    rows = base_answer(con)
    if not rows or "summary" not in rows[0]:
        return rows
    return [rows[0]]


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
