"""Q12.xx / RQ-h1-017 -- How does each repo's code volume grow over time?

The bank's phrasing asks for a split into "authored, generated, vendored" --
commit_files has no such flag (no generator marker, no vendored-path list
per repo), so this reports the split the data actually supports instead:
code / test / docs / config / other, by extension, as cumulative net lines
(insertions - deletions) per repo per month. Renaming a file shows as a
delete + add pair in git.py's --no-renames log, which very slightly inflates
both insertions and deletions on a rename-heavy month without changing net.
"""
RQ_ID = "RQ-h1-017"
QUESTION = "How does each repo's code volume grow over time, by rough file category?"

CODE_EXT = {"go", "ts", "tsx", "js", "jsx", "py", "rs", "java", "rb", "c", "cpp", "h", "hpp"}
TEST_EXT_HINT = None  # tests are usually identified by path, not extension; see _category
DOCS_EXT = {"md", "html", "txt"}
CONFIG_EXT = {"yaml", "yml", "json", "toml", "tf", "mod", "sum", "cfg", "ini", "sh"}


def _category(path, ext):
    p = path.lower()
    if "_test." in p or "/test" in p or p.startswith("test") or ".test." in p or "/tests/" in p:
        return "test"
    if ext in CODE_EXT:
        return "code"
    if ext in DOCS_EXT:
        return "docs"
    if ext in CONFIG_EXT:
        return "config"
    return "other"


SQL = """
SELECT cf.repo, c.month, cf.path, cf.ext, cf.insertions, cf.deletions
FROM git.commit_files cf
JOIN git.commits c ON c.repo = cf.repo AND c.sha = cf.sha
WHERE c.month IS NOT NULL
"""


def answer(con):
    rows = con.execute(SQL).fetchall()
    agg = {}
    for r in rows:
        cat = _category(r["path"], (r["ext"] or "").lower())
        key = (r["repo"], r["month"], cat)
        agg.setdefault(key, 0)
        agg[key] += (r["insertions"] or 0) - (r["deletions"] or 0)

    by_repo_cat = {}
    out = []
    for (repo, month, cat), net in sorted(agg.items()):
        rk = (repo, cat)
        by_repo_cat[rk] = by_repo_cat.get(rk, 0) + net
        out.append({"repo": repo, "month": month, "category": cat, "net_lines_this_month": net,
                     "cumulative_net_lines": by_repo_cat[rk]})
    return out


if __name__ == "__main__":
    from cube.db import connect
    for row in answer(connect()):
        print(row)
