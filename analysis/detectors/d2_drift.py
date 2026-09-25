"""D2 drift intervals -> detectors.sqlite, table drift.

Full scope per the plan needs three signals: vendored hash vs source,
template-file-vs-clone-file at each clone commit, and a DESIGN.md-untouched-
while-architecture-changed check. Only the first is buildable from what's
ingested today, and only for ONE path: knowledge.instruction_files carries a
`vendored_hash` per (repo, path) at each repo's own HEAD, but a "source of
truth" row to diff against only exists for `.claude/rules/comments.md` --
the process plugin's own checkout (fleet.PLUGIN_REPO_NAME) carries that
exact path on every wayfare-skills-based fleet (it's the rule Claude Code
loads directly from the plugin, so the plugin's own copy IS the canonical
source, generically). Every other vendored path (hooks, other rules,
skills) lives at a DIFFERENT path inside the plugin (under assets/, per
AGENTS.md: "assets/ is installed into other repos"), so there is no
same-path row in the plugin repo to diff a consumer's copy against --
computing their drift would need ingest/knowledge.py extended to also hash
the plugin's assets/ source files per path-mapping, which it doesn't do.
This detector is a real, correct signal for one path, not the ten-artifact
scan the plan describes; treat it as a seed for the rest, not a substitute.

No interval (start/end of divergence) either -- instruction_files is a
current-HEAD snapshot, not per-commit history, so "drift is present right
now" is all this can say; when it started needs a git-log walk of the file
this pass doesn't do.
"""
import os, sqlite3, sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ingest.fleet import OUT, PLUGIN_REPO_NAME

DB_PATH = os.path.join(OUT, "detectors.sqlite")
KNOWLEDGE_DB = os.path.join(OUT, "knowledge.sqlite")
SOURCE_REPO = PLUGIN_REPO_NAME
TRACKED_PATH = ".claude/rules/comments.md"


def build():
    con = sqlite3.connect(KNOWLEDGE_DB)
    source_row = con.execute(
        "SELECT vendored_hash, updated_ts FROM instruction_files WHERE repo = ? AND path = ?",
        (SOURCE_REPO, TRACKED_PATH),
    ).fetchone()

    out = []
    if source_row:
        source_hash, source_ts = source_row
        for repo, vendored_hash, updated_ts in con.execute(
            "SELECT repo, vendored_hash, updated_ts FROM instruction_files WHERE path = ? AND repo != ?",
            (TRACKED_PATH, SOURCE_REPO),
        ).fetchall():
            drifted = 1 if vendored_hash != source_hash else 0
            out.append((TRACKED_PATH, repo, drifted, updated_ts, source_ts))
    con.close()

    outdb = sqlite3.connect(DB_PATH)
    outdb.execute("DROP TABLE IF EXISTS drift")
    outdb.execute("""
        CREATE TABLE drift (
            artifact TEXT, repo TEXT, drifted_now INTEGER,
            repo_last_touched_ts TEXT, source_last_touched_ts TEXT
        )
    """)
    outdb.executemany("INSERT INTO drift VALUES (?,?,?,?,?)", out)
    outdb.commit()
    n_drifted = sum(1 for r in out if r[2])
    print(f"detectors.sqlite: drift {len(out)} repos checked for {TRACKED_PATH}, {n_drifted} currently drifted")
    outdb.close()


if __name__ == "__main__":
    build()
