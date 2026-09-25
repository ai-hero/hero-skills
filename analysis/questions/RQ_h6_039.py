"""Q10.xx / RQ-h6-039 -- Do the plugin's verification skills end with an
explicit verdict? Live read of skills/*/SKILL.md (this checkout): a skill
"verifies" if its name/content suggests review/audit/check, and "ends with
an explicit verdict" if it contains PASS/FAIL/verdict language.
"""
import glob, os, re

RQ_ID = "RQ-h6-039"
QUESTION = "Do the plugin's verification skills end with an explicit verdict?"

SKILLS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "skills")
VERIFY_NAME_RE = re.compile(r"review|audit|check|verify|ship", re.I)
VERDICT_RE = re.compile(r"\bPASS\b|\bFAIL\b|verdict", re.I)


def answer(con=None):
    out = []
    for skill_md in sorted(glob.glob(os.path.join(SKILLS_DIR, "*", "SKILL.md"))):
        name = os.path.basename(os.path.dirname(skill_md))
        if not VERIFY_NAME_RE.search(name):
            continue
        text = open(skill_md, errors="replace").read()
        out.append({"skill": name, "has_explicit_verdict_language": bool(VERDICT_RE.search(text))})
    return out


if __name__ == "__main__":
    for row in answer():
        print(row)
