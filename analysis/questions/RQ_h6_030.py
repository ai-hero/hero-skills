"""Q5.xx / RQ-h6-030 -- Which repos in the fleet show no recorded use of the
process plugin?

"Use" = at least one tool_calls row with a skill_name set, joined through
sessions.repo. A repo with sessions but none of its tool calls carrying a
skill_name genuinely never invoked a wayfare skill in the transcripts we
have (from 2026-08-09 on) -- earlier use, if any, is outside the window.
"""
RQ_ID = "RQ-h6-030"
QUESTION = "Which repos in the fleet show no recorded use of the process plugin?"

SQL = """
SELECT s.repo,
       COUNT(DISTINCT s.session_id_hash) AS sessions,
       COUNT(DISTINCT CASE WHEN t.skill_name IS NOT NULL THEN t.session_id_hash END) AS sessions_using_a_skill,
       COUNT(DISTINCT t.skill_name) AS distinct_skills_used
FROM harness.sessions s
LEFT JOIN harness.tool_calls t ON t.session_id_hash = s.session_id_hash
GROUP BY s.repo
ORDER BY sessions_using_a_skill ASC
"""


def answer(con):
    return con.execute(SQL).fetchall()


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(dict(row))
