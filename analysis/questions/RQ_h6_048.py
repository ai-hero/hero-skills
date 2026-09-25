"""Q10.xx / RQ-h6-048 -- How often does an agent's judgment call get
reversed by the owner or a later work item? Haiku-backed proxy: the
'correction' kind from detectors.prompt_kind, as a share of all flagged
prompts and of all prompts fleet-wide (a floor, since only regex-flagged
prompts were ever classified).
"""
RQ_ID = "RQ-h6-048"
QUESTION = "How often does an agent's judgment call get reversed by the owner?"


def answer(con):
    total_prompts = con.execute("SELECT COUNT(*) FROM harness.prompts WHERE is_slash_command = 0").fetchone()[0]
    corrections = con.execute(
        "SELECT COUNT(*) FROM detectors.prompt_kind_by_prompt p "
        "JOIN detectors.prompt_kind pk ON pk.content_hash = p.content_hash "
        "WHERE p.flagged = 1 AND pk.kind = 'correction'"
    ).fetchone()[0]
    return [{"total_non_slash_prompts": total_prompts, "classified_as_correction": corrections,
             "floor_share_of_all_prompts": round(corrections / total_prompts, 4)}]


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
