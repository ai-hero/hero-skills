"""Q13.xx / NEW-C07-G -- What share of found work is absorbed into the
current change versus filed as its own item?
item_edges.kind='discovered_from' is what makes it into the store at all
(a distinct item, "filed as its own"); work absorbed into the same commit
with no separate item leaves no edge -- so this reports discovered_from
edges as the filed-separately count, against total items, as an upper
bound on the filed share (absorbed work is invisible here by definition,
not zero).
"""
RQ_ID = "NEW-C07-G"
QUESTION = "What share of found work is absorbed into the current change versus filed as its own item?"


def answer(con):
    filed = con.execute(
        "SELECT COUNT(*) FROM plans.item_edges WHERE kind = 'discovered_from'"
    ).fetchone()[0]
    total_items = con.execute("SELECT COUNT(*) FROM plans.plan_items WHERE type != 'goal'").fetchone()[0]
    return [{
        "items_filed_as_found_work": filed, "total_items": total_items,
        "filed_share_of_all_items": round(filed / total_items, 3),
        "note": "absorbed-not-filed work leaves no record, so this is a floor on filed "
                "found work, not a filed-vs-absorbed split",
    }]


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
