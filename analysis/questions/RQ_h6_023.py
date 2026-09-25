"""Q10.xx / RQ-h6-023 -- How does each repo pin the process plugin: a
moving reference, a tag, or a fixed commit?

Not a cube query: the answer isn't in any per-repo file at all.
~/.claude/plugins/installed_plugins.json is a single MACHINE-wide install
(scope: "user"), pinned to one gitCommitSha -- every repo on this machine
gets whatever that one checkout currently is, all at once, on the next
`claude` launch. There is no per-repo pin to read. Reads live local state,
not an ingested table, so this can drift from what a re-run reports if the
plugin gets updated in between -- by design, since "what commit is pinned
right now" is the question.
"""
import json, os

RQ_ID = "RQ-h6-023"
QUESTION = "How does each repo pin the process plugin: a moving reference, a tag, or a fixed commit?"

INSTALLED_PLUGINS = os.path.expanduser("~/.claude/plugins/installed_plugins.json")


def answer(con=None):
    if not os.path.exists(INSTALLED_PLUGINS):
        return [{"answerable": False, "reason": f"{INSTALLED_PLUGINS} not found"}]
    data = json.load(open(INSTALLED_PLUGINS))
    out = []
    for key, installs in data.get("plugins", data).items():
        if not isinstance(installs, list):
            continue
        for inst in installs:
            out.append({
                "plugin": key, "scope": inst.get("scope"), "version": inst.get("version"),
                "git_commit_sha": inst.get("gitCommitSha"), "last_updated": inst.get("lastUpdated"),
            })
    return out


if __name__ == "__main__":
    for row in answer():
        print(row)
