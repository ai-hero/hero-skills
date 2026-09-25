"""Q10.xx / RQ-h6-004 -- How much of a clone's code is new product surface
versus copied template boilerplate?
Proxy: for each clone, the share of its current file paths that also exist
at the same path in the template's current tree (git ls-tree at HEAD,
paths only -- content isn't diffed, so an edited-but-still-present file
still counts as "shared path," not "new").
"""
import subprocess, os, sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ingest.fleet import ALL_REPOS, path_of, GROUPS, TEMPLATE_REPO

RQ_ID = "RQ-h6-004"
QUESTION = "How much of a clone's code is new product surface versus copied template boilerplate?"


def tree_paths(path):
    p = subprocess.run(["git", "-C", path, "ls-tree", "-r", "--name-only", "HEAD"], capture_output=True, text=True)
    return set(p.stdout.splitlines()) if p.returncode == 0 else set()


def answer(con=None):
    if not TEMPLATE_REPO:
        return [{"note": "no FLEET.md group: template repo in this fleet"}]
    template_paths = tree_paths(path_of(TEMPLATE_REPO))
    if not template_paths:
        return [{"note": f"could not read {TEMPLATE_REPO}'s tree"}]
    out = []
    for repo, group in GROUPS.items():
        if group != "apps":
            continue
        paths = tree_paths(path_of(repo))
        if not paths:
            continue
        shared = len(paths & template_paths)
        out.append({"repo": repo, "files": len(paths), "shared_path_with_template": shared,
                    "new_surface_share": round(1 - shared / len(paths), 3)})
    return out


if __name__ == "__main__":
    for row in answer():
        print(row)
