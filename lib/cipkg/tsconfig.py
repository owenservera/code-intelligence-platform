"""tsconfig.json-aware import resolution: baseUrl, paths aliases, JSONC comments."""
import json, os

def _strip_jsonc(text):
    out, i, n, in_str = [], 0, len(text), False
    while i < n:
        ch = text[i]
        if in_str:
            out.append(ch)
            if ch == "\\" and i + 1 < n:
                out.append(text[i + 1]); i += 2; continue
            if ch == '"': in_str = False
            i += 1; continue
        if ch == '"':
            in_str = True; out.append(ch); i += 1; continue
        if ch == "/" and i + 1 < n and text[i + 1] == "/":
            while i < n and text[i] != "\n": i += 1
            continue
        if ch == "/" and i + 1 < n and text[i + 1] == "*":
            i += 2
            while i + 1 < n and not (text[i] == "*" and text[i + 1] == "/"): i += 1
            i += 2; continue
        out.append(ch); i += 1
    return "".join(out)

class TSResolver:
    def __init__(self, root):
        self.root = root
        self.base_dir = root
        self.paths = {}
        self.enabled = True
        self._load()

    def _load(self):
        p = os.path.join(self.root, "tsconfig.json")
        if not os.path.exists(p):
            self.enabled = False; return
        try:
            cfg = json.loads(_strip_jsonc(open(p, encoding="utf-8").read()))
        except Exception:
            self.enabled = False; return
        co = cfg.get("compilerOptions", {}) or {}
        base = co.get("baseUrl", ".")
        self.base_dir = os.path.normpath(os.path.join(os.path.dirname(p), base)).replace(os.sep, "/")
        self.paths = co.get("paths", {}) or {}

    def _ext_cands(self, base):
        exts = (".ts", ".tsx", ".js", ".jsx", ".mjs", ".d.ts")
        base = base.replace(os.sep, "/")
        return [base] + [base + e for e in exts] + [base + "/index" + e for e in exts[:4]]

    def candidates(self, spec, from_path):
        out = []
        for pat, targets in self.paths.items():
            if pat.endswith("/*"):
                pre = pat[:-2]
                if spec == pre or spec.startswith(pre + "/"):
                    rest = "" if spec == pre else spec[len(pre) + 1:]
                    for t in targets:
                        t2 = t[:-2] if t.endswith("/*") else t
                        out += self._ext_cands(os.path.normpath(os.path.join(self.base_dir, t2, rest)))
            elif pat == spec:
                for t in targets:
                    out += self._ext_cands(os.path.normpath(os.path.join(self.base_dir, t)))
        out += self._ext_cands(os.path.normpath(os.path.join(self.base_dir, spec)))
        seen, rel = set(), []
        for c in out:
            r = os.path.relpath(c, self.root).replace(os.sep, "/")
            if r not in seen:
                seen.add(r); rel.append(r)
        return rel
