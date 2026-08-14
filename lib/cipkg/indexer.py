"""Incremental, content-hashed indexer with scoped edge rebuild and
dependency-aware embedding refresh. This is the self-updating heart of CIP."""
import os, re, time
from .base import repo_root, load_config, iter_files, sha, is_test_path
from .store import connect, get_meta, set_meta
from .detect import lang_for
from .parsers import parse_file
from .parse import extract_imports
from .embed import get_embedder, to_blob

IDENT = re.compile(r"[A-Za-z_$][A-Za-z0-9_$]*")
STOP_NAMES = {"get", "set", "run", "init", "main", "test", "call", "apply", "handle",
              "value", "data", "item", "result", "args", "kwargs", "self", "this",
              "super", "error", "len", "range", "print", "console", "then", "catch",
              "keys", "values", "push", "map", "filter", "reduce", "find", "name"}
RES_EXTS = (".ts", ".tsx", ".js", ".jsx", ".mjs", ".py", ".rs", ".go")

def resolve_import(src_path, spec, all_paths):
    spec = spec.strip()
    if spec.startswith("."):
        base = os.path.normpath(os.path.join(os.path.dirname(src_path), spec)).replace(os.sep, "/")
        cands = [base] + [base + e for e in RES_EXTS]
        cands += [base + "/index" + e for e in RES_EXTS[:4]]
        for c in cands:
            if c in all_paths: return c
    elif re.fullmatch(r"[\w.]+", spec):
        base = spec.replace(".", "/")
        for c in (base + ".py", base + "/__init__.py"):
            if c in all_paths: return c
    return None

def index_file(con, path, source, h, size, mtime):
    language = lang_for(path)
    parsed = parse_file(path, language, source)
    con.execute("DELETE FROM symbols WHERE path=?", (path,))
    con.execute("DELETE FROM chunks WHERE path=?", (path,))
    con.execute("DELETE FROM edges WHERE src_path=?", (path,))
    con.execute("DELETE FROM file_imports WHERE path=?", (path,))
    con.execute("DELETE FROM vectors WHERE id LIKE ?", (path + "#%",))
    con.execute("INSERT OR REPLACE INTO files(path,language,size,lines,hash,mtime,indexed_at) "
                "VALUES(?,?,?,?,?,?,?)",
                (path, language, size, source.count("\n") + 1, h, mtime, time.time()))
    for s in parsed["symbols"]:
        con.execute("INSERT OR REPLACE INTO symbols"
                    "(id,name,kind,path,start_line,end_line,signature,body_hash,body) "
                    "VALUES(?,?,?,?,?,?,?,?,?)",
                    (s["id"], s["name"], s["kind"], path, s["start"], s["end"],
                     s["signature"], s["body_hash"], s["body"]))
        con.execute("INSERT OR IGNORE INTO edges(src,dst,kind,src_path) VALUES(?,?,?,?)",
                    (path, s["id"], "contains", path))
        if s["exported"]:
            con.execute("INSERT OR IGNORE INTO edges(src,dst,kind,src_path) VALUES(?,?,?,?)",
                        (path, s["id"], "exports", path))
    for c in parsed["chunks"]:
        con.execute("INSERT OR REPLACE INTO chunks"
                    "(id,path,symbol_id,start_line,end_line,text,text_hash) VALUES(?,?,?,?,?,?,?)",
                    (c["id"], path, c.get("symbol_id"), c["start"], c["end"], c["text"], c["hash"]))
    for spec in parsed["imports"]:
        con.execute("INSERT INTO file_imports(path,spec) VALUES(?,?)", (path, spec))

def remove_file(con, path):
    con.execute("DELETE FROM files WHERE path=?", (path,))
    con.execute("DELETE FROM symbols WHERE path=?", (path,))
    con.execute("DELETE FROM chunks WHERE path=?", (path,))
    con.execute("DELETE FROM edges WHERE src_path=?", (path,))
    con.execute("DELETE FROM edges WHERE dst=?", (path,))
    con.execute("DELETE FROM file_imports WHERE path=?", (path,))
    con.execute("DELETE FROM vectors WHERE id LIKE ?", (path + "#%",))

def link_imports(con, dirty, all_paths):
    paths = ([r["path"] for r in con.execute("SELECT path FROM files")]
             if dirty is None else list(dirty))
    for p in paths:
        con.execute("DELETE FROM edges WHERE src_path=? AND kind='imports'", (p,))
        for r in con.execute("SELECT spec FROM file_imports WHERE path=?", (p,)):
            tgt = resolve_import(p, r["spec"], all_paths)
            if tgt and tgt != p:
                con.execute("INSERT OR IGNORE INTO edges(src,dst,kind,src_path) VALUES(?,?,?,?)",
                            (p, tgt, "imports", p))

def resolve_symbol_edges(con, cfg, dirty):
    name_map = {}
    for r in con.execute("SELECT id, name, path FROM symbols"):
        if r["name"] in STOP_NAMES or len(r["name"]) < 4: continue
        name_map.setdefault(r["name"], []).append((r["id"], r["path"]))
    if dirty is None:
        con.execute("DELETE FROM edges WHERE kind IN ('calls','references')")
        rows = con.execute("SELECT id, path, body FROM symbols").fetchall()
    else:
        if not dirty: return build_tested_by(con, cfg)
        ph = ",".join("?" * len(dirty))
        con.execute(f"DELETE FROM edges WHERE kind IN ('calls','references') AND src_path IN ({ph})", list(dirty))
        rows = con.execute(f"SELECT id, path, body FROM symbols WHERE path IN ({ph})", list(dirty)).fetchall()
    for row in rows:
        body = row["body"] or ""
        seen = 0
        for m in IDENT.finditer(body):
            if seen > 200: break
            hits = name_map.get(m.group(0))
            if not hits: continue
            kind = "calls" if body[m.end():m.end() + 4].lstrip().startswith("(") else "references"
            for (tid, _tp) in hits:
                if tid == row["id"]: continue
                con.execute("INSERT OR IGNORE INTO edges(src,dst,kind,src_path) VALUES(?,?,?,?)",
                            (row["id"], tid, kind, row["path"]))
                seen += 1
    build_tested_by(con, cfg)

def build_tested_by(con, cfg):
    con.execute("DELETE FROM edges WHERE kind='tested_by'")
    test_files = [r["path"] for r in con.execute("SELECT path FROM files")
                  if is_test_path(r["path"], cfg)]
    for tf in test_files:
        targets = {r["dst"] for r in con.execute(
            "SELECT dst FROM edges WHERE src_path=? AND kind IN ('imports','calls','references')", (tf,))}
        for t in targets:
            srow = con.execute("SELECT path FROM symbols WHERE id=?", (t,)).fetchone()
            if srow and srow["path"] != tf:
                con.execute("INSERT OR IGNORE INTO edges(src,dst,kind,src_path) VALUES(?,?,?,?)",
                            (t, tf, "tested_by", srow["path"]))

def embed_pending(con, cfg, batch=64, progress=None):
    """Embed unembedded chunks. Returns count embedded.
    progress(phase, current, total) called per batch."""
    cached = get_meta(con, "embedder_name")
    if cached:
        n = con.execute("SELECT COUNT(*) c FROM chunks c LEFT JOIN vectors v "
                        "ON v.id=c.id AND v.model=? WHERE v.id IS NULL", (cached,)).fetchone()["c"]
        if n == 0:
            con.execute("DELETE FROM vectors WHERE model <> ?", (cached,))
            return 0
    emb = get_embedder(cfg)
    set_meta(con, "embedder_name", emb.name)
    total = 0
    total_chunks = con.execute("SELECT COUNT(*) c FROM chunks c LEFT JOIN vectors v "
                               "ON v.id=c.id AND v.model=? WHERE v.id IS NULL",
                               (emb.name,)).fetchone()["c"]
    while True:
        rows = con.execute("SELECT c.id, c.text FROM chunks c LEFT JOIN vectors v "
                           "ON v.id=c.id AND v.model=? WHERE v.id IS NULL LIMIT ?",
                           (emb.name, batch)).fetchall()
        if not rows: break
        for r, v in zip(rows, emb.embed([r["text"] for r in rows])):
            con.execute("INSERT OR REPLACE INTO vectors(id,model,vec) VALUES(?,?,?)",
                        (r["id"], emb.name, to_blob(v)))
        con.commit()
        total += len(rows)
        if progress:
            progress("embed", total, total_chunks)
    con.execute("DELETE FROM vectors WHERE id NOT IN (SELECT id FROM chunks)")
    con.execute("DELETE FROM vectors WHERE model <> ?", (emb.name,))
    return total

def compute_stats(con):
    q = lambda t: con.execute(f"SELECT COUNT(*) c FROM {t}").fetchone()["c"]
    return {"files": q("files"), "symbols": q("symbols"), "chunks": q("chunks"),
            "edges": q("edges"), "vectors": q("vectors")}

def sync(root=None, full=False, do_embed=True, progress=None):
    """Index repo. progress(phase, current, total) for long operations."""
    root = root or repo_root()
    cfg = load_config(root)
    con = connect(root)
    t0 = time.time()
    known = {r["path"]: (r["hash"], r["mtime"])
             for r in con.execute("SELECT path, hash, mtime FROM files")}
    all_paths, dirty, deleted = set(known), [], list(known)
    # Phase 1: scan files
    file_list = list(iter_files(root, cfg))
    if progress:
        progress("scan", 0, len(file_list))
    scanned = 0
    for rel in file_list:
        ap = os.path.join(root, rel)
        try: st = os.stat(ap)
        except OSError: continue
        if rel in known: deleted.remove(rel)
        kh = known.get(rel)
        if kh and kh[1] == st.st_mtime and not full:
            scanned += 1
            if progress and scanned % 50 == 0:
                progress("scan", scanned, len(file_list))
            continue                                        # mtime fast path
        try:
            with open(ap, encoding="utf-8", errors="replace") as f: src = f.read()
        except OSError: continue
        h = sha(src)
        if kh and kh[0] == h and not full:
            con.execute("UPDATE files SET mtime=? WHERE path=?", (st.st_mtime, rel))
            scanned += 1
            if progress and scanned % 50 == 0:
                progress("scan", scanned, len(file_list))
            continue                                        # content unchanged
        index_file(con, rel, src, h, st.st_size, st.st_mtime)
        dirty.append(rel)
        all_paths.add(rel)
        scanned += 1
        if progress and scanned % 10 == 0:
            progress("scan", scanned, len(file_list))
    if progress:
        progress("scan", len(file_list), len(file_list))
    # Phase 2: deleted
    for rel in deleted:
        remove_file(con, rel)
        all_paths.discard(rel)
    # Phase 3: link edges
    if dirty or deleted or full:
        if progress:
            progress("link", 0, 0)
        link_imports(con, dirty or None, all_paths)
        resolve_symbol_edges(con, cfg, dirty or None)
        from .parsers import build_heritage
        build_heritage(con, dirty or None)
        con.commit()
        if progress:
            progress("link", 1, 1)
    # Phase 4: embed (optional)
    n_emb = 0
    if do_embed:
        def _emb_prog(phase, cur, tot):
            if progress: progress("embed", cur, tot)
        n_emb = embed_pending(con, cfg, progress=_emb_prog)
    stats = compute_stats(con)
    stats.update(dirty=len(dirty), deleted=len(deleted), embedded=n_emb,
                 ms=int((time.time() - t0) * 1000))
    set_meta(con, "last_sync", time.time())
    con.execute("INSERT INTO events(ts,kind,payload) VALUES(?,?,?)",
                (time.time(), "sync", str(stats)))
    con.commit()
    return stats
