"""Q10.xx / NEW-C10-02 -- For each skill, what share of its steps is a
script versus prose instructions, week by week?

Not a cube query: reads the live skills/ tree in this checkout (the "week
by week" half of the question needs per-commit history of each SKILL.md,
which isn't ingested -- this answers only the current-state split).
"script step" = a fenced code block (```bash, ```python, a `scripts/*`
reference); "prose step" = a numbered or bulleted list item outside a code
fence. A crude line-shape heuristic, not a parse of the skill's actual
control flow.
"""
import glob, os, re

RQ_ID = "NEW-C10-02"
QUESTION = "For each skill, what share of its steps is a script versus prose instructions?"

SKILLS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "skills")
FENCE_RE = re.compile(r"```")
LIST_ITEM_RE = re.compile(r"^\s*[-*]\s+|\s*\d+\.\s+")
SCRIPT_REF_RE = re.compile(r"scripts/\S+\.(sh|py|js)")


def answer(con=None):
    out = []
    for skill_md in sorted(glob.glob(os.path.join(SKILLS_DIR, "*", "SKILL.md"))):
        name = os.path.basename(os.path.dirname(skill_md))
        text = open(skill_md, errors="replace").read()
        script_blocks = len(FENCE_RE.findall(text)) // 2
        script_refs = len(SCRIPT_REF_RE.findall(text))
        prose_steps = len([l for l in text.splitlines() if LIST_ITEM_RE.match(l)])
        script_steps = script_blocks + script_refs
        total = script_steps + prose_steps
        if total:
            out.append({"skill": name, "script_steps": script_steps, "prose_steps": prose_steps,
                        "script_share": round(script_steps / total, 3)})
    return out


if __name__ == "__main__":
    for row in answer():
        print(row)
