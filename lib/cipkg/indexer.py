"""Incremental, content-hashed indexer with scoped edge rebuild and
dependency-aware embedding refresh. This is the self-updating heart of CIP.

v2 performance architecture
---------------------------
* File reading + symbol/chunk parsing is parallelised across worker processes
  (Windows `spawn`-safe: the parse worker only receives path/source text, never
  a DB connection or unpicklable tree-sitter objects).
* All writes are batched with `executemany` -- a repo with tens of thousands of
  symbols collapses into a handful of bulk statements per sync instead of one
  INSERT per symbol/chunk.
* Vector KNN is served from a cached matrix (see store.vector_matrix), so
  repeated searches don't reload the whole embedding table.
"""
import os, re, time
from concurrent.futures import ProcessPoolExecutor, as_completed
from .base import repo_root, load_config, sha, is_test_path, tokenize
from .gatekeeper import iter_files_smart, chunk_markdown
from .tsconfig import TSResolver
from .store import (connect, get_meta, set_meta, bulk, bulk_delete_paths,
                    invalidate_vectors)
from .detect import lang_for
from .parsers import parse_file
from .embed import get_embedder, to_blob
from .base import sha as _sha

IDENT = re.compile(r"[A-Za-z_$][A-Za-z0-9_$]*")
STOP_NAMES = {"get", "set", "run", "init", "main", "test", "call", "apply", "handle",
               "value", "data", "item", "result", "args", "kwargs", "self", "this",
               "super", "error", "len", "range", "print", "console", "then", "catch",
               "keys", "values", "push", "map", "filter", "reduce", "find", "name"}
RES_EXTS = (".ts", ".tsx", ".js", ".jsx", ".mjs", ".py", ".rs", ".go")

_TS_RESOLVERS = {}
def _get_ts_resolver(root):
    if root not in _TS_RESOLVERS:
        _TS_RESOLVERS[root] = TSResolver(root)
    return _TS_RESOLVERS[root]

def resolve_import(src_path, spec, all_paths, resolver=None):
    """Resolve an import spec to a repo-root-relative path, or None.

    Python specs keep their leading dots (``from .base import``, ``from ..stack.audit
    import``); the relative branch must convert those into real parent hops and
    emit a plain repo path (never a ``lib/cipkg/.base.py`` artifact — F-22).
    Absolute repo-local specs (``cipkg.module``) are tried under the common
    source roots ``lib/`` and ``src/``.
    """
    spec = spec.strip()
    if spec.startswith("."):
        m = re.match(r"^\.+", spec)
        levels = m.end()
        rest = spec[levels:]
        base_dir = os.path.dirname(src_path)
        for _ in range(levels - 1):       # "." = sibling dir; ".." = one up, ...
            base_dir = os.path.dirname(base_dir)
        if rest:
            # Dotted names are always package separators: ``stack.common`` is the
            # submodule ``stack/common``, never a literal ``stack.common`` file.
            mod = rest.replace(".", "/")
            core = os.path.normpath(os.path.join(base_dir, mod)).replace(os.sep, "/")
            cands = [core + "/__init__.py"] + [core + e for e in RES_EXTS] \
                + [core + "/index" + e for e in RES_EXTS]
        else:                              # `from . import x` - the dir is the package
            core = os.path.normpath(base_dir).replace(os.sep, "/")
            cands = [core + "/__init__.py"]
        for c in cands:
            if c in all_paths:
                return c
    elif re.fullmatch(r"[\w.]+", spec):
        base = spec.replace(".", "/")
        for pref in ("", "lib/", "src/"):
            for c in (base + "/__init__.py", base + ".py"):
                if pref + c in all_paths:
                    return pref + c
    if resolver and resolver.enabled:                 # tsconfig aliases
        for c in resolver.candidates(spec, src_path):
            if c in all_paths: return c
    return None

# -- parallel parse worker (top-level so ProcessPoolExecutor can pickle it) --

def _parse_worker(job):
    path, language, source, tier = job
    if tier != "code":
        return (path, None)
    try:
        return (path, parse_file(path, language, source))
    except Exception:
        return (path, None)

# -- prepare (pure, picklable inputs) ------------------------------------------

def prepare_file(rel, tier, source, h, size, mtime, parsed):
    """Return a dict of rows to upsert for one file. No DB access here, so it
    is safe to run inside a worker process."""
    language = lang_for(rel)
    lines = source.count("\n") + 1
    file_row = (rel, language, size, lines, h, mtime, time.time(), tier)
    symbols, sym_edges, chunks, imports, calls = [], [], [], [], []
    if tier == "code" and parsed:
        qmap = {s["qualname"]: s["id"] for s in parsed["symbols"]}
        for s in parsed["symbols"]:
            symbols.append((s["id"], s["name"], s["kind"], rel, s["start"],
                            s["end"], s["signature"], s["body_hash"], s["body"]))
            sym_edges.append((rel, s["id"], "contains", rel))
            if s["exported"]:
                sym_edges.append((rel, s["id"], "exports", rel))
        for spec in parsed["imports"]:
            imports.append((rel, spec))
        for (caller_qual, callee) in (parsed.get("calls") or []):
            sid = qmap.get(caller_qual)
            if sid:
                calls.append((sid, callee))
        for c in parsed["chunks"]:
            chunks.append((c["id"], rel, c.get("symbol_id"), c["start"], c["end"],
                           c["text"], _sha(c["text"]), " ".join(tokenize(c["text"]))))
    elif tier == "doc":
        for c in chunk_markdown(rel, source):
            chunks.append((c["id"], rel, None, c["start"], c["end"], c["text"],
                           _sha(c["text"]), " ".join(tokenize(c["text"]))))
    elif tier == "config":
        text = "\n".join(source.splitlines()[:60])
        end = min(60, max(1, source.count("\n") + 1))
        chunks.append((f"{rel}#L1-L{end}", rel, None, 1, end, text,
                       _sha(text), " ".join(tokenize(text))))
    return {"file": file_row, "symbols": symbols, "sym_edges": sym_edges,
            "chunks": chunks, "imports": imports, "calls": calls}

def _noop():
    return []

def _bulk_write(con, prepared):
    """Upsert a list of prepared file dicts in a few batched statements."""
    if not prepared:
        return
    paths = [p["file"][0] for p in prepared]
    chunk_ids = [c[0] for p in prepared for c in p["chunks"]]
    sym_ids = [s[0] for p in prepared for s in p["symbols"]]
    # 1. delete old rows for these files (chunk/vector fk first)
    if chunk_ids:
        bulk_delete_paths(con, "vectors", "id", chunk_ids)
    if sym_ids:
        bulk_delete_paths(con, "symbol_calls", "symbol_id", sym_ids)
    bulk_delete_paths(con, "symbols", "path", paths)
    bulk_delete_paths(con, "chunks", "path", paths)
    bulk_delete_paths(con, "edges", "src_path", paths)
    bulk_delete_paths(con, "file_imports", "path", paths)
    # 2. insert
    bulk(con, "INSERT OR REPLACE INTO files"
              "(path,language,size,lines,hash,mtime,indexed_at,tier) VALUES(?,?,?,?,?,?,?,?)",
         [p["file"] for p in prepared])
    bulk(con, "INSERT OR REPLACE INTO symbols"
              "(id,name,kind,path,start_line,end_line,signature,body_hash,body) "
              "VALUES(?,?,?,?,?,?,?,?,?)",
         [s for p in prepared for s in p["symbols"]])
    bulk(con, "INSERT OR REPLACE INTO chunks"
              "(id,path,symbol_id,start_line,end_line,text,text_hash,tokens) "
              "VALUES(?,?,?,?,?,?,?,?)",
         [c for p in prepared for c in p["chunks"]])
    bulk(con, "INSERT OR IGNORE INTO edges(src,dst,kind,src_path) VALUES(?,?,?,?)",
         [e for p in prepared for e in p["sym_edges"]])
    bulk(con, "INSERT INTO file_imports(path,spec) VALUES(?,?)",
         [i for p in prepared for i in p["imports"]])
    bulk(con, "INSERT INTO symbol_calls(symbol_id,callee_name) VALUES(?,?)",
         [c for p in prepared for c in p["calls"]])

# -- back-compat single-file entry point ---------------------------------------

def index_file(con, path, source, h, size, mtime, tier="code"):
    parsed = parse_file(path, lang_for(path), source) if tier == "code" else None
    _bulk_write(con, [prepare_file(path, tier, source, h, size, mtime, parsed)])
    con.commit()

def remove_file(con, path):
    chunk_ids = [r[0] for r in con.execute(
        "SELECT id FROM chunks WHERE path=?", (path,)).fetchall()]
    sym_ids = [r[0] for r in con.execute(
        "SELECT id FROM symbols WHERE path=?", (path,)).fetchall()]
    if chunk_ids:
        bulk_delete_paths(con, "vectors", "id", chunk_ids)
    if sym_ids:
        bulk_delete_paths(con, "symbol_calls", "symbol_id", sym_ids)
    bulk_delete_paths(con, "symbols", "path", [path])
    bulk_delete_paths(con, "chunks", "path", [path])
    bulk_delete_paths(con, "edges", "src_path", [path])
    bulk_delete_paths(con, "edges", "dst", [path])
    bulk_delete_paths(con, "file_imports", "path", [path])

def link_imports(con, dirty, all_paths, root=None):
    resolver = _get_ts_resolver(root) if root else None
    paths = ([r["path"] for r in con.execute("SELECT path FROM files")]
             if dirty is None else list(dirty))
    new_edges = []
    for p in paths:
        con.execute("DELETE FROM edges WHERE src_path=? AND kind='imports'", (p,))
        for r in con.execute("SELECT spec FROM file_imports WHERE path=?", (p,)):
            tgt = resolve_import(p, r["spec"], all_paths, resolver)
            if tgt and tgt != p:
                new_edges.append((p, tgt, "imports", p))
    bulk(con, "INSERT OR IGNORE INTO edges(src,dst,kind,src_path) VALUES(?,?,?,?)",
         new_edges)

def resolve_symbol_edges(con, cfg, dirty):
    name_map = {}
    for r in con.execute("SELECT id, name, path FROM symbols"):
        if r["name"] in STOP_NAMES or len(r["name"]) < 4: continue
        name_map.setdefault(r["name"], []).append((r["id"], r["path"]))
    imports_by_file = {}
    for e in con.execute("SELECT src_path, dst FROM edges WHERE kind='imports'"):
        imports_by_file.setdefault(e["src_path"], set()).add(e["dst"])
    tree_calls = {}
    for r in con.execute("SELECT symbol_id, callee_name FROM symbol_calls"):
        tree_calls.setdefault(r["symbol_id"], set()).add(r["callee_name"])
    if dirty is None:
        con.execute("DELETE FROM edges WHERE kind IN ('calls','references')")
        rows = con.execute("SELECT id, path, body FROM symbols").fetchall()
    else:
        if not dirty: return build_tested_by(con, cfg)
        ph = ",".join("?" * len(dirty))
        con.execute(f"DELETE FROM edges WHERE kind IN ('calls','references') AND src_path IN ({ph})", list(dirty))
        rows = con.execute(f"SELECT id, path, body FROM symbols WHERE path IN ({ph})", list(dirty)).fetchall()
    new_edges = []
    for row in rows:
        body = row["body"] or ""
        allowed = {row["path"]} | imports_by_file.get(row["path"], set())
        seen = 0
        if row["id"] in tree_calls:
            cand_names = tree_calls[row["id"]]
        else:
            cand_names = [m.group(0) for m in IDENT.finditer(body)]
        for name in cand_names:
            if seen > 200: break
            hits = name_map.get(name)
            if not hits: continue
            for (tid, tpath) in hits:
                if tid == row["id"]: continue
                if tpath not in allowed: continue      # v1.2 import-scope precision gate
                new_edges.append((row["id"], tid, "calls", row["path"]))
                seen += 1
    bulk(con, "INSERT OR IGNORE INTO edges(src,dst,kind,src_path) VALUES(?,?,?,?)",
         new_edges)
    build_tested_by(con, cfg)

def _is_backup_path(path: str) -> bool:
    """True for a repo path under a backup/duplicate/generated tree.

    Segment-aware (agrees with `tests/detectors/s6_index_integrity._is_backup_rel`):
    a path segment that IS `backups`/`htmlcov`, starts `backup_`/`emergency_`, or
    ends `.bak`/`.orig`. Test filenames merely *containing* "backup_" are not.
    """
    return any(
        seg == "backups" or seg == "htmlcov"
        or seg.startswith(("backup_", "emergency_"))
        or seg.endswith((".bak", ".orig"))
        for seg in path.replace("\\", "/").split("/")
    )

def build_tested_by(con, cfg):
    """Build tested_by edges from test files to the symbols they test.

    F-23: only symbols the test file *actually* imports/calls/references count.
    No more name-mention matching against chunk text (that produced ~4.5k
    invented edges from every symbol whose name merely appeared in a test file's
    first chunk). Symbols living under backup/duplicate paths are dropped, and
    edges keep the product convention `src` = tested symbol, `dst` = test file.
    """
    con.execute("DELETE FROM edges WHERE kind='tested_by'")
    test_files = [r["path"] for r in con.execute("SELECT path FROM files")
                  if is_test_path(r["path"], cfg)]
    new_edges = []
    for tf in test_files:
        # Real imports/calls/references from this test file → symbol ids. After
        # F-22 the `imports` edges actually resolve, so tested_by is grounded in
        # the import graph instead of the name-mention heuristic.
        targets = {r["dst"] for r in con.execute(
            "SELECT dst FROM edges WHERE src_path=? AND kind IN ('imports','calls','references')", (tf,))}
        for t in targets:
            srow = con.execute("SELECT id, path FROM symbols WHERE id=?", (t,)).fetchone()
            if not srow or srow["path"] == tf:
                continue
            if _is_backup_path(srow["path"]):
                continue           # backup/duplicate symbols are never "tested"
            new_edges.append((srow["id"], tf, "tested_by", srow["path"]))

    if new_edges:
        bulk(con, "INSERT OR IGNORE INTO edges(src,dst,kind,src_path) VALUES(?,?,?,?)",
             new_edges)

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
    print("  loading embedding model...", end="", flush=True)
    emb = get_embedder(cfg)
    print(f" done ({emb.name})")
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
        vecs = emb.embed([r["text"] for r in rows])
        bulk(con, "INSERT OR REPLACE INTO vectors(id,model,vec) VALUES(?,?,?)",
             [(r["id"], emb.name, to_blob(v)) for r, v in zip(rows, vecs)])
        con.commit()
        total += len(rows)
        if progress:
            progress("embed", total, total_chunks)
    con.execute("DELETE FROM vectors WHERE id NOT IN (SELECT id FROM chunks)")
    con.execute("DELETE FROM vectors WHERE model <> ?", (emb.name,))
    invalidate_vectors(con)          # free any cached matrix in this process
    return total

def compute_stats(con):
    q = lambda t: con.execute(f"SELECT COUNT(*) c FROM {t}").fetchone()["c"]
    return {"files": q("files"), "symbols": q("symbols"), "chunks": q("chunks"),
            "edges": q("edges"), "vectors": q("vectors")}

def _sync_body(root=None, full=False, do_embed=True, progress=None):
    """Index repo. progress(phase, current, total) for long operations."""
    root = root or repo_root()
    cfg = load_config(root)
    con = connect(root)
    t0 = time.time()
    known = {r["path"]: (r["hash"], r["mtime"])
             for r in con.execute("SELECT path, hash, mtime FROM files")}
    all_paths, dirty, deleted = set(known), [], list(known)
    # Phase 1: scan files (serial, fast I/O) -- find what actually changed
    print("  [1/4] Scanning files for changes...", flush=True) if progress else None
    file_list = list(iter_files_smart(root, cfg))
    if progress:
        progress("scan", 0, len(file_list))
    scanned = 0
    jobs = []          # (rel, tier, source, h, size, mtime)
    for rel, tier, _why in file_list:
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
        jobs.append((rel, tier, src, h, st.st_size, st.st_mtime))
        dirty.append(rel)
        all_paths.add(rel)
        scanned += 1
        if progress and scanned % 10 == 0:
            progress("scan", scanned, len(file_list))
    if progress:
        progress("scan", len(file_list), len(file_list))

    # Phase 1b: parallel parse (CPU-bound) across worker processes
    parsed_map = {}
    code_jobs = [(rel, lang_for(rel), src, tier) for (rel, tier, src, *_)
                 in jobs if tier == "code"]
    if code_jobs:
        print("  [1.5/4] Parsing %d files (parallel)..." % len(code_jobs),
              flush=True) if progress else None
        workers = int(cfg.get("perf", {}).get("workers", 0) or 0)
        use_pool = workers != 1
        try:
            if use_pool:
                nw = workers or (os.cpu_count() or 1)
                with ProcessPoolExecutor(max_workers=nw) as ex:
                    futs = {ex.submit(_parse_worker, j): j[0] for j in code_jobs}
                    for fut in as_completed(futs):
                        p, res = fut.result()
                        parsed_map[p] = res
            else:
                for j in code_jobs:
                    p, res = _parse_worker(j)
                    parsed_map[p] = res
        except Exception:
            for j in code_jobs:
                p, res = _parse_worker(j)
                parsed_map[p] = res

    prepared = [prepare_file(rel, tier, src, h, size, mtime, parsed_map.get(rel))
                for (rel, tier, src, h, size, mtime) in jobs]
    _bulk_write(con, prepared)
    con.commit()

    # Phase 2: deleted
    if deleted:
        print(f"  [2/4] Removing {len(deleted)} deleted files...", flush=True) if progress else None
    for rel in deleted:
        remove_file(con, rel)
        all_paths.discard(rel)

    # Phase 3: link edges
    if dirty or deleted or full:
        print(f"  [3/4] Linking relationships ({len(dirty)} changed files)...",
              flush=True) if progress else None
        if progress:
            progress("link", 0, 0)
        link_imports(con, dirty or None, all_paths, root)
        resolve_symbol_edges(con, cfg, dirty or None)
        from .parsers import build_heritage
        build_heritage(con, dirty or None)
        con.commit()
        if progress:
            progress("link", 1, 1)

    # Phase 4: embed (optional)
    n_emb = 0
    if do_embed:
        print(f"  [4/4] Embedding for semantic search...", flush=True) if progress else None
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
    # SPEC-04 §6.1: durable job snapshot (post-commit, off the hot path).
    # sync computes counts only; audit/consolidate jobs fill health/components.
    from .store import write_snapshot
    write_snapshot(con, "sync", health=None,
                   counts={"files": stats.get("files"), "symbols": stats.get("symbols"),
                           "chunks": stats.get("chunks"), "edges": stats.get("edges"),
                           "vectors": stats.get("vectors")},
                   meta={"dirty": stats.get("dirty"), "deleted": stats.get("deleted"),
                         "embedded": stats.get("embedded"), "ms": stats.get("ms")})
    return stats

def sync(root=None, full=False, do_embed=True, progress=None):
    from .lock import WriteLock
    root = root or repo_root()
    with WriteLock(root):
        return _sync_body(root, full, do_embed, progress)
