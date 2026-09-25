"""D4 found-work chains -> detectors.sqlite, table found_work.

item_edges.kind='discovered_from' (repo, src_item -> dst_repo, dst_item) is
already a normalized cross-store graph from ingest/plans.py. This resolves
each edge into a root (walk discovered_from until no further parent),
depth (hops from root) and the root's total fan-out (children at depth 1).
A cycle (shouldn't exist, but nothing enforces it) is broken by capping walk
length at 50 hops and flagging cycle_broken -- silently mis-rooting a cycle
would be worse than a visible flag.
"""
import os, sqlite3, sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ingest.fleet import OUT

DB_PATH = os.path.join(OUT, "detectors.sqlite")
PLANS_DB = os.path.join(OUT, "plans.sqlite")
MAX_DEPTH = 50


def build():
    pcon = sqlite3.connect(PLANS_DB)
    edges = pcon.execute(
        "SELECT repo, src_item, dst_repo, dst_item FROM item_edges WHERE kind = 'discovered_from'"
    ).fetchall()
    # child (repo,item) -> parent (repo,item) it was discovered from
    parent_of = {(repo, src): (dst_repo, dst_item) for repo, src, dst_repo, dst_item in edges}
    children_of = {}
    for repo, src, dst_repo, dst_item in edges:
        children_of.setdefault((dst_repo, dst_item), []).append((repo, src))

    rows = []
    for repo, src, dst_repo, dst_item in edges:
        node, depth, cycle_broken = (repo, src), 0, 0
        seen = {node}
        while node in parent_of and depth < MAX_DEPTH:
            node = parent_of[node]
            depth += 1
            if node in seen:
                cycle_broken = 1
                break
            seen.add(node)
        root = node
        fan_out = len(children_of.get(root, []))
        rows.append((repo, src, root[0], root[1], depth, fan_out, cycle_broken))

    con = sqlite3.connect(DB_PATH)
    con.execute("DROP TABLE IF EXISTS found_work")
    con.execute("""
        CREATE TABLE found_work (
            repo TEXT, item_id TEXT, root_repo TEXT, root_item_id TEXT,
            depth INTEGER, root_fan_out INTEGER, cycle_broken INTEGER
        )
    """)
    con.executemany("INSERT INTO found_work VALUES (?,?,?,?,?,?,?)", rows)
    con.commit()
    print(f"detectors.sqlite: found_work {len(rows)} rows, "
          f"{len({(r[2], r[3]) for r in rows})} distinct roots, "
          f"max depth {max((r[4] for r in rows), default=0)}")
    con.close()
    pcon.close()


if __name__ == "__main__":
    build()
