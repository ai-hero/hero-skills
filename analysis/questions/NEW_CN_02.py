"""Q6.xx / NEW-CN-02 -- How often is a connector's value copied into a
repo instead of read from its source? Proxy: repos whose HERO.md
`## Connections` reach is "checkout" (a local copy) versus "auto"/live
(read from source), from NEW-CN-01's parser.
"""
RQ_ID = "NEW-CN-02"
QUESTION = "How often is a connector's value copied into a repo instead of read from its source?"


def answer(con):
    from questions.NEW_CN_01 import answer as base_answer
    rows = base_answer(None)
    with_reach = [r for r in rows if isinstance(r, dict) and r.get("reach")]
    copied = sum(1 for r in with_reach if r["reach"] == "checkout")
    return [{"connectors_with_a_reach_value": len(with_reach), "copied_local": copied,
             "read_live": len(with_reach) - copied}]


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
