"""Symbol extraction. Zero-dependency regex engine (always works);
higher-fidelity backends (tree-sitter) plug in via RULES."""
import re
from .base import sha

STOPWORDS = {"if", "for", "while", "switch", "catch", "return", "new", "else",
             "do", "try", "case", "typeof", "delete", "void", "await", "yield"}

def _c(pat, flags=0): return re.compile(pat, flags)

RULES = {
    "python": [
        (_c(r"^(\s*)class\s+(\w+)"), "class"),
        (_c(r"^(\s*)(?:async\s+)?def\s+(\w+)\s*\("), "function"),
    ],
    "typescript": [
        (_c(r"^(\s*)(?:export\s+)?(?:default\s+)?(?:abstract\s+)?class\s+(\w+)"), "class"),
        (_c(r"^(\s*)(?:export\s+)?interface\s+(\w+)"), "interface"),
        (_c(r"^(\s*)(?:export\s+)?type\s+(\w+)\s*="), "type"),
        (_c(r"^(\s*)(?:export\s+)?enum\s+(\w+)"), "class"),
        (_c(r"^(\s*)(?:export\s+)?(?:default\s+)?(?:async\s+)?function\s*\*?\s*([\w$]+)"), "function"),
        (_c(r"^(\s*)(?:export\s+)?(?:const|let|var)\s+([\w$]+)\s*=\s*(?:async\s*)?(?:\(|[\w$]+\s*=>)"), "function"),
        (_c(r"^(\s{2,})(?:(?:public|private|protected|static|async|readonly|get|set)\s+)*([\w$]+)\s*\([^)]*\)\s*[:{]"), "method"),
    ],
    "rust": [
        (_c(r"^(\s*)(?:pub(?:\([^)]*\))?\s+)?(?:struct|enum|trait)\s+(\w+)"), "class"),
        (_c(r"^(\s*)(?:pub(?:\([^)]*\))?\s+)?(?:async\s+)?fn\s+(\w+)"), "function"),
    ],
    "go": [
        (_c(r"^(\s*)type\s+(\w+)\s+(?:struct|interface)"), "class"),
        (_c(r"^func\s+(?:\([^)]*\)\s*)?(\w+)"), "function"),
    ],
}
RULES["javascript"] = RULES["typescript"][0:1] + RULES["typescript"][4:7]
RULES["java"] = RULES["csharp"] = [
    (_c(r"^(\s*)(?:public\s+|final\s+|abstract\s+|static\s+)*class\s+(\w+)"), "class"),
    (_c(r"^(\s{2,})(?:public|private|protected|static|final|async|\s)+[\w<>\[\]]+\s+(\w+)\s*\([^)]*\)\s*{"), "method"),
]

GENERIC = [
    (_c(r"^(\s*)class\s+(\w+)"), "class"),
    (_c(r"^(\s*)(?:def|function|func|fn)\s+(\w+)"), "function"),
]

INDENT_LANGS = {"python"}

IMPORT_PATS = {
    "typescript": [_c(r"""from\s+['"]([^'"]+)['"]"""),
                   _c(r"""import\s*\(\s*['"]([^'"]+)['"]"""),
                   _c(r"""require\(\s*['"]([^'"]+)['"]""")],
    "python":     [_c(r"^\s*from\s+([\w.]+)\s+import", re.M),
                   _c(r"^\s*import\s+([\w.]+)", re.M)],
    "go":         [_c(r'^\s*(?:\w+\s+)?"([\w./\-]+)"', re.M)],
    "rust":       [_c(r"^\s*(?:pub\s+)?mod\s+(\w+)\s*;", re.M)],
}
IMPORT_PATS["javascript"] = IMPORT_PATS["typescript"]

def _indent_of(line):
    return len(line) - len(line.lstrip())

def _end_indent(lines, i):
    base = _indent_of(lines[i])
    for j in range(i + 1, len(lines)):
        if not lines[j].strip(): continue
        if _indent_of(lines[j]) <= base:
            return j            # 1-based last line of the block
    return len(lines)

def _end_braces(lines, i):
    depth, started = 0, False
    for j in range(i, len(lines)):
        for ch in lines[j]:
            if ch == "{": depth += 1; started = True
            elif ch == "}": depth -= 1
            if started and depth == 0:
                return j + 1
    return i + 1 if not started else len(lines)

def extract_imports(source, language):
    out = []
    for rx in IMPORT_PATS.get(language, []):
        out.extend(m.group(1) for m in rx.finditer(source))
    return out

def parse_file(path, language, source):
    lines = source.splitlines()
    rules = RULES.get(language, GENERIC)
    indent_lang = language in INDENT_LANGS
    raw = []
    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped or stripped.startswith(("//", "#", "*", "/*")):
            continue
        for rx, kind in rules:
            m = rx.match(line)
            if not m: continue
            name = m.group(2)
            if name in STOPWORDS: break
            end = _end_indent(lines, i) if indent_lang else _end_braces(lines, i)
            raw.append({"name": name, "kind": kind, "start": i + 1, "end": end,
                        "line": stripped})
            break

    classes = [s for s in raw if s["kind"] == "class"]
    symbols = []
    for s in raw:
        qual = s["name"]
        kind = s["kind"]
        if kind == "function":
            parent = next((c for c in classes
                           if c["start"] < s["start"] and s["end"] <= c["end"]), None)
            if parent:
                qual, kind = f'{parent["name"]}.{s["name"]}', "method"
        body = "\n".join(lines[s["start"] - 1:s["end"]])
        symbols.append({
            "id": f"{language}://{path}#{qual}",
            "name": s["name"], "kind": kind, "qualname": qual,
            "start": s["start"], "end": s["end"],
            "signature": s["line"][:240],
            "exported": s["line"].startswith(("export", "pub ")),
            "body": body, "body_hash": sha(body),
        })

    chunks = []
    for s in symbols:
        text = "\n".join(lines[s["start"] - 1:s["end"]])
        chunks.append({"id": f'{path}#L{s["start"]}-L{s["end"]}', "path": path,
                       "symbol_id": s["id"], "start": s["start"], "end": s["end"],
                       "text": text, "hash": sha(text)})
    if not symbols and lines:
        n = min(60, len(lines))
        text = "\n".join(lines[:n])
        chunks.append({"id": f"{path}#L1-L{n}", "path": path, "symbol_id": None,
                       "start": 1, "end": n, "text": text, "hash": sha(text)})

    return {"symbols": symbols, "imports": extract_imports(source, language), "chunks": chunks}
