"""Q10.xx / NEW-C10-04 -- Is the process plugin versioned and vendored into
every repo from one source?

Reads ~/.claude/plugins/installed_plugins.json for the plugin's pinned
gitCommitSha and install scope. A "user" scope is one machine-wide install,
not a copy written into each repo's tree the way assets/ (rules, hooks) is
(see detectors/d2_drift.py).
"""
import json, os, sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ingest.fleet import PLUGIN_REPO_NAME

RQ_ID = "NEW-C10-04"
QUESTION = "Is the process plugin versioned and vendored into every repo from one source?"

INSTALLED_PLUGINS = os.path.expanduser("~/.claude/plugins/installed_plugins.json")


def answer(con=None):
    entry = None
    if os.path.exists(INSTALLED_PLUGINS):
        data = json.load(open(INSTALLED_PLUGINS))
        for key, installs in data.get("plugins", {}).items():
            if key.startswith(PLUGIN_REPO_NAME + "@") and installs:
                entry = installs[0]
    return [{
        "versioned": entry is not None and entry.get("gitCommitSha") is not None,
        "pinned_sha": entry.get("gitCommitSha") if entry else None,
        "vendored_into_every_repo": False,
        "actual_mechanism": "one machine-wide plugin install (scope=user), shared by every repo, "
                             "not a per-repo vendored copy",
    }]


if __name__ == "__main__":
    for row in answer():
        print(row)
