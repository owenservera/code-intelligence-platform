"""Pluggable parsing v1.0.
Default: zero-dep regex engine (v0.9). Upgrade by installing grammars:
    pip install tree-sitter tree-sitter-python tree-sitter-typescript \
                tree-sitter-javascript tree-sitter-rust tree-sitter-go
Any failure falls back to regex — parsing never breaks indexing."""
from .base import sha
from .parse import parse_file as regex_parse, extract_imports
import re

_LOADERS = {
    "python":     ("tree_sitter_python", "language_python"),
    "typescript": ("tree_sitter_typescript", "language_typescript"),
    "javascript": ("tree_sitter_javascript", "language_javascript"),
    "rust":       ("tree_sitter_rust", "language_rust"),
    "go":         ("tree_sitter_go", "language_go"),
}
_LANG_CACHE = {}

NODE_KINDS = {
    "python": {"class_definition": "class", "function_definition": "function"},
    "typescript": {"class_declaration": "class", "function_declaration": "function",
                   "method_definition": "method", "interface_declaration": "interface",
                   "type_alias_declaration": "type", "enum_declaration": "class"},
    "rust": {"struct_item": "class", "enum_item": "class", "trait_item": "interface",
             "function_item": "function"},
    "go": {"function_declaration": "function", "method_declaration": "method",
           "type_declaration": "class"},
}
NODE_KINDS["javascript"] = {k: v for k, v in NODE_KINDS["typescript"].items()
                            if k not in ("interface_declaration", "type_alias_declaration")}

def _get_language(language):
    if language in _LANG_CACHE: return _LANG_CACHE[language]
    spec = _LOADERS.get(language)
    if not spec:
        _LANG_CACHE[language] = None
        return None
    try:
        import importlib
        from tree_sitter import Language
        mod = importlib.import_module(spec[0])
        lang = Language(getattr(mod, spec[1])())
        if language == "typescript":
            try: _LANG_CACHE["tsx"] = Language(getattr(mod, "language_tsx")())
            except Exception: pass
        _LANG_CACHE[language] = lang
        return lang
    except Exception:
        _LANG_CACHE[language] = None
        return None

def _mk_sym(path, language, name, kind, start, end, lines, body, exported, class_name=None):
    if class_name and kind in ("function", "method"):
        kind, qual = "method", f"{class_name}.{name}"
    else:
        qual = name
    sig = lines[start - 1].strip()[:240] if 0 < start <= len(lines) else name
    return {"id": f"{language}://{path}#{qual}", "name": name, "kind": kind,
            "qualname": qual, "start": start, "end": end, "signature": sig,
            "exported": exported, "body": body, "body_hash": sha(body)}

def _ts_parse(path, language, source, lang):
    from tree_sitter import Parser
    if path.endswith(".tsx") and _LANG_CACHE.get("tsx"):
        lang = _LANG_CACHE["tsx"]
    parser = Parser()
    try: parser.language = lang
    except Exception: parser.set_language(lang)
    tree = parser.parse(source.encode("utf-8"))
    kinds = NODE_KINDS.get(language, NODE_KINDS["typescript"])
    lines = source.splitlines()
    syms, seen = [], set()

    def add(node, kind, name, class_name):
        start, end = node.start_point[0] + 1, node.end_point[0] + 1
        body = source[node.start_byte:node.end_byte]
        exported = node.parent is not None and node.parent.type == "export_statement"
        s = _mk_sym(path, language, name, kind, start, end, lines, body, exported, class_name)
        if s["id"] not in seen:
            seen.add(s["id"]); syms.append(s)

    def walk(node, class_name):
        t = node.type
        if t in kinds:
            nn = node.child_by_field_name("name")
            if nn is not None:
                add(node, kinds[t], source[nn.start_byte:nn.end_byte], class_name)
        elif t == "lexical_declaration":
            for ch in node.children:
                if ch.type != "variable_declarator": continue
                vn = ch.child_by_field_name("name")
                val = ch.child_by_field_name("value")
                if vn is not None and val is not None and val.type in (
                        "arrow_function", "function_expression", "function"):
                    add(ch, "function", source[vn.start_byte:vn.end_byte], class_name)
        next_class = class_name
        if t in ("class_declaration", "class_definition", "struct_item",
                 "trait_item", "interface_declaration"):
            nn = node.child_by_field_name("name")
            if nn is not None:
                next_class = source[nn.start_byte:nn.end_byte]
        for ch in node.children:
            walk(ch, next_class)

    walk(tree.root_node, None)

    chunks = []
    for s in syms:
        text = "\n".join(lines[s["start"] - 1:s["end"]])
        chunks.append({"id": f'{path}#L{s["start"]}-L{s["end"]}', "path": path,
                       "symbol_id": s["id"], "start": s["start"], "end": s["end"],
                       "text": text, "hash": sha(text)})
    if not syms and lines:
        n = min(60, len(lines))
        text = "\n".join(lines[:n])
        chunks.append({"id": f"{path}#L1-L{n}", "path": path, "symbol_id": None,
                       "start": 1, "end": n, "text": text, "hash": sha(text)})
    return {"symbols": syms, "imports": extract_imports(source, language), "chunks": chunks}

def parse_file(path, language, source):
    lang = _get_language(language)
    if lang is not None:
        try:
            return _ts_parse(path, language, source, lang)
        except Exception:
            pass
    return regex_parse(path, language, source)

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
