"""Pluggable parsing v1.0.

Single robust entry point: delegate to cipkg.parse.parse_file, which uses
tree-sitter (real call edges, Unicode-safe byte slicing) for every supported
language and falls back to the zero-dependency regex engine. Parsing never
breaks indexing. build_heritage() resolves extends/implements edges.
"""
from .parse import parse_file as _backend_parse, extract_imports
from .base import sha
import re


def parse_file(path, language, source):
    # One engine for all languages: tree-sitter (Python/TS/JS/… with call
    # edges + correct multibyte handling) with automatic regex fallback.
    # The earlier duplicate tree-sitter path here lacked Python support and
    # sliced str with byte offsets (corrupting every symbol after a non-ASCII
    # char); it has been removed in favour of cipkg.parse / cipkg.tree_parser.
    return _backend_parse(path, language, source)


HERITAGE = re.compile(r"\b(extends|implements)\s+([A-Za-z_$][\w$]*)")


def build_heritage(con, dirty):
    """extends/implements edges by name resolution (works for both backends)."""
    if dirty is None:
        con.execute("DELETE FROM edges WHERE kind IN ('extends','implements')")
        rows = con.execute("SELECT id, path, body FROM symbols").fetchall()
    else:
        if not dirty: return
        ph = ",".join("?" * len(dirty))
        con.execute(f"DELETE FROM edges WHERE kind IN ('extends','implements') AND src_path IN ({ph})",
                    list(dirty))
        rows = con.execute(f"SELECT id, path, body FROM symbols WHERE path IN ({ph})",
                           list(dirty)).fetchall()
    name_index = {}
    for r in con.execute("SELECT id, name FROM symbols WHERE kind IN ('class','interface')"):
        name_index.setdefault(r["name"], r["id"])
    for row in rows:
        n = 0
        for m in HERITAGE.finditer(row["body"] or ""):
            if n > 20: break
            kind, name = m.group(1), m.group(2)
            dst = name_index.get(name)
            if dst and dst != row["id"]:
                con.execute("INSERT OR IGNORE INTO edges(src,dst,kind,src_path) VALUES(?,?,?,?)",
                            (row["id"], dst, kind, row["path"]))
                n += 1
