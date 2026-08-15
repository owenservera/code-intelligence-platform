"""Tree-sitter parser: accurate symbols + real call edges for TS/TSX/JS/Python.
Falls back to the regex parser automatically if grammars are missing."""
from .base import sha

try:
    from tree_sitter import Language, Parser
    _TS = True
except Exception:
    _TS = False

_LANGS = {}
def _load():
    global _LANGS
    if not _TS or _LANGS:
        return _LANGS
    try:
        import tree_sitter_typescript as t
        _LANGS["typescript"] = Language(t.language_typescript())
        _LANGS["tsx"] = Language(t.language_tsx())
    except Exception: pass
    try:
        import tree_sitter_javascript as j
        _LANGS["javascript"] = Language(j.language())
    except Exception: pass
    try:
        import tree_sitter_python as p
        _LANGS["python"] = Language(p.language())
    except Exception: pass
    return _LANGS

def available(lang):
    return lang in _load()

def _parser(lang):
    L = _load()[lang]
    try:
        return Parser(L)
    except TypeError:
        p = Parser(); p.set_language(L); return p

DEF_NODES = {
    "class_declaration": "class", "abstract_class_declaration": "class",
    "function_declaration": "function", "method_definition": "method",
    "interface_declaration": "interface", "type_alias_declaration": "type",
    "enum_declaration": "class",
    # python
    "class_definition": "class", "function_definition": "function",
}

def parse(path, source, language):
    lang_key = "tsx" if path.endswith(".tsx") else language
    if lang_key not in _load():
        return None
    parser = _parser(lang_key)
    src_bytes = source.encode("utf-8")
    tree = parser.parse(src_bytes)
    lines = source.split("\n")
    symbols, calls = [], []

    def txt(n): return src_bytes[n.start_byte:n.end_byte].decode("utf-8", "replace")
    def exported(node):
        p = node.parent
        while p:
            if p.type == "export_statement": return True
            if p.type in ("program", "module"): break
            p = p.parent
        return False

    def emit(node, name, kind, class_scope, span=None):
        sn = span or node
        start, end = sn.start_point[0] + 1, sn.end_point[0] + 1
        if class_scope and kind in ("function", "method"):
            kind, qual = "method", f"{class_scope}.{name}"
        else:
            qual = name
        body = "\n".join(lines[start - 1:end])
        symbols.append({
            "id": f"{language}://{path}#{qual}", "name": name, "kind": kind,
            "qualname": qual, "start": start, "end": end,
            "signature": (lines[start - 1].strip()[:240] if start - 1 < len(lines) else ""),
            "exported": exported(sn), "body": body, "body_hash": sha(body),
        })
        return qual

    def capture_call(node, func_qual):
        if not func_qual: return
        fn = node.child_by_field_name("function")
        if not fn: return
        callee = None
        if fn.type == "identifier": callee = txt(fn)
        elif fn.type == "member_expression":
            prop = fn.child_by_field_name("property")
            if prop: callee = txt(prop)
        if callee: calls.append((func_qual, callee))

    def walk(node, class_scope, func_qual):
        t = node.type
        child_class, child_func = class_scope, func_qual
        if t in DEF_NODES:
            nn = node.child_by_field_name("name")
            if nn:
                qual = emit(node, txt(nn), DEF_NODES[t], class_scope)
                if DEF_NODES[t] in ("class",): child_class = txt(nn)
                else: child_func = qual
        elif t in ("lexical_declaration", "variable_declaration"):
            for ch in node.named_children:
                if ch.type != "variable_declarator": continue
                nm = ch.child_by_field_name("name")
                val = ch.child_by_field_name("value")
                if nm and val and val.type in ("arrow_function", "function_expression",
                                               "function", "generator_function"):
                    child_func = emit(ch, txt(nm), "function", class_scope, span=node)
        elif t == "call_expression":
            capture_call(node, func_qual)
        for c in node.children:
            walk(c, child_class, child_func)

    walk(tree.root_node, None, None)

    # chunks: one per symbol, else file header
    chunks = []
    for s in symbols:
        text = "\n".join(lines[s["start"] - 1:s["end"]])
        chunks.append({"id": f"{path}#L{s['start']}-L{s['end']}", "path": path,
                       "symbol_id": s["id"], "start": s["start"], "end": s["end"],
                       "text": text, "hash": sha(text)})
    if not symbols and lines:
        n = min(60, len(lines)); text = "\n".join(lines[:n])
        chunks.append({"id": f"{path}#L1-L{n}", "path": path, "symbol_id": None,
                       "start": 1, "end": n, "text": text, "hash": sha(text)})

    from .parse import extract_imports
    return {"symbols": symbols, "imports": extract_imports(source, language),
            "chunks": chunks, "calls": calls}
