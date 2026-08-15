"""Hierarchical summaries: repo → dir → file. Structural (offline) by default;
optional LLM backend. Hash-cached → dependency-aware invalidation for free:
a summary regenerates only when its content hash drifts."""
import datetime, os, time
from .base import repo_root, load_config, sha
from .store import connect

def _file_hash(con, path):
    r = con.execute("SELECT hash FROM files WHERE path=?", (path,)).fetchone()
    return r["hash"] if r else None

def _struct_file_summary(con, path):
    syms = con.execute("SELECT name, kind FROM symbols WHERE path=? ORDER BY start_line",
                       (path,)).fetchall()
    imps = con.execute("SELECT COUNT(*) c FROM edges WHERE src_path=? AND kind='imports'",
                       (path,)).fetchone()["c"]
    tests = [r["dst"] for r in con.execute(
        "SELECT DISTINCT dst FROM edges WHERE kind='tested_by' AND src_path=?", (path,))]
    fails = con.execute("SELECT COUNT(*) c FROM signals WHERE path=? AND kind='test_fail'",
                        (path,)).fetchone()["c"]
    terrs = con.execute("SELECT COUNT(*) c FROM signals WHERE path=? AND kind='type_error'",
                        (path,)).fetchone()["c"]
    last = con.execute("SELECT c.message, c.ts FROM commit_files cf JOIN commits c "
                       "ON c.sha=cf.sha WHERE cf.path=? ORDER BY c.ts DESC LIMIT 1",
                       (path,)).fetchone()
    lines = [f"{path}: {len(syms)} symbols, {imps} imports."]
    if syms:
        names = ", ".join(f"{s['kind']} {s['name']}" for s in syms[:12])
        lines.append(f"Defines: {names}" + (" …" if len(syms) > 12 else ""))
    if tests: lines.append(f"Tested by: {', '.join(tests[:3])}")
    if fails: lines.append(f"WARNING: {fails} failing test signal(s)")
    if terrs: lines.append(f"WARNING: {terrs} type error(s)")
    if last:
        d = datetime.datetime.fromtimestamp(last["ts"]).strftime("%Y-%m-%d")
        lines.append(f"Last change: {d} — {last['message'][:80]}")
    return "\n".join(lines)

def _llm_summary(base_text, cfg):
    try:
        import json, urllib.request
        key = os.environ["OPENAI_API_KEY"]
        model = cfg["summary"].get("llm_model", "gpt-4o-mini")
        req = urllib.request.Request(
            "https://api.openai.com/v1/chat/completions",
            data=json.dumps({"model": model, "max_tokens": 160,
                             "messages": [
                                 {"role": "system", "content": "Summarize this code unit in 3 factual sentences."},
                                 {"role": "user", "content": base_text}]}).encode(),
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=60) as r:
            data = json.load(r)
        return data["choices"][0]["message"]["content"].strip()
    except Exception:
        return None

def file_summary(root, path):
    con = connect(root); cfg = load_config(root)
    h = _file_hash(con, path)
    if h is None:
        return {"path": path, "error": "not indexed"}
    sid = f"file://{path}"
    row = con.execute("SELECT summary, content_hash, source FROM summaries WHERE id=?",
                      (sid,)).fetchone()
    if row and row["content_hash"] == h:
        return {"path": path, "summary": row["summary"], "source": row["source"], "cached": True}
    summary, src = _struct_file_summary(con, path), "structural"
    if cfg["summary"].get("backend") == "llm":
        llm = _llm_summary(summary, cfg)
        if llm:
            summary, src = llm, f'llm:{cfg["summary"].get("llm_model")}'
    con.execute("INSERT OR REPLACE INTO summaries(id,kind,path,content_hash,summary,source,updated_at) "
                "VALUES(?,?,?,?,?,?,?)", (sid, "file", path, h, summary, src, time.time()))
    con.commit()
    return {"path": path, "summary": summary, "source": src, "cached": False}

def dir_summary(root, path):
    con = connect(root)
    prefix = path.rstrip("/") + "/"
    rows = con.execute("SELECT path, hash FROM files WHERE path LIKE ?", (prefix + "%",)).fetchall()
    if not rows:
        return {"path": path, "error": "unknown directory"}
    h = sha("|".join(sorted(r["hash"] for r in rows)))
    sid = f"dir://{path}"
    cached = con.execute("SELECT summary, content_hash, source FROM summaries WHERE id=?",
                         (sid,)).fetchone()
    if cached and cached["content_hash"] == h:
        return {"path": path, "summary": cached["summary"], "source": cached["source"], "cached": True}
    nsym = con.execute("SELECT COUNT(*) c FROM symbols WHERE path LIKE ?", (prefix + "%",)).fetchone()["c"]
    names = [r["path"] for r in rows[:20]]
    summary = (f"{path}: {len(rows)} files, {nsym} symbols.\n"
               f"Files: {', '.join(names)}" + (" …" if len(rows) > 20 else ""))
    con.execute("INSERT OR REPLACE INTO summaries(id,kind,path,content_hash,summary,source,updated_at) "
                "VALUES(?,?,?,?,?,?,?)", (sid, "dir", path, h, summary, "structural", time.time()))
    con.commit()
    return {"path": path, "summary": summary, "source": "structural", "cached": False}

def _repo_summary(root, con, cfg):
    import json as _json
    stats = {t: con.execute(f"SELECT COUNT(*) c FROM {t}").fetchone()["c"]
             for t in ("files", "symbols", "edges", "commits", "signals")}
    det = con.execute("SELECT value FROM meta WHERE key='detection'").fetchone()
    det = _json.loads(det["value"]) if det else {}
    h = sha(str(stats) + str(det.get("primary")))
    sid = "repo://"
    cached = con.execute("SELECT summary, content_hash FROM summaries WHERE id=?", (sid,)).fetchone()
    if cached and cached["content_hash"] == h:
        return {"path": None, "summary": cached["summary"], "source": "structural", "cached": True}
    lines = [f"Repository: primary language {det.get('primary', 'unknown')}, "
             f"stacks {det.get('stacks', [])}.",
             f"{stats['files']} files, {stats['symbols']} symbols, {stats['edges']} relationships."]
    if stats["commits"]: lines.append(f"{stats['commits']} commits indexed.")
    if stats["signals"]: lines.append(f"{stats['signals']} runtime signals ingested.")
    try:
        from .gitindex import hotspots
        hs = hotspots(root, k=5)
        if hs:
            lines.append("Hotspots: " + ", ".join(f"{x['path']} ({x['score']})" for x in hs))
    except Exception:
        pass
    summary = "\n".join(lines)
    con.execute("INSERT OR REPLACE INTO summaries(id,kind,path,content_hash,summary,source,updated_at) "
                "VALUES(?,?,?,?,?,?,?)", (sid, "repo", None, h, summary, "structural", time.time()))
    con.commit()
    return {"path": None, "summary": summary, "source": "structural", "cached": False}

def summary(root=None, path=None):
    root = root or repo_root()
    if not path or path in (".", "/"):
        return _repo_summary(root, connect(root), load_config(root))
    path = path.strip("/")
    con = connect(root)
    if con.execute("SELECT 1 FROM files WHERE path=?", (path,)).fetchone():
        return file_summary(root, path)
    return dir_summary(root, path)

def map_(root=None):
    root = root or repo_root(); con = connect(root)
    files = [r["path"] for r in con.execute("SELECT path FROM files")]
    dirs = {}
    for p in files:
        parts = p.split("/")
        top = parts[0] if len(parts) > 1 else "(root)"
        d = dirs.setdefault(top, {"files": 0, "symbols": 0})
        d["files"] += 1
    for name, d in dirs.items():
        if name == "(root)":
            d["symbols"] = con.execute(
                "SELECT COUNT(*) c FROM symbols WHERE path NOT LIKE '%/%'").fetchone()["c"]
        else:
            d["symbols"] = con.execute(
                "SELECT COUNT(*) c FROM symbols WHERE path LIKE ?",
                (name + "/%",)).fetchone()["c"]
    try:
        from .gitindex import hotspots
        hs = hotspots(root, k=5)
    except Exception:
        hs = []
    return {"directories": [{"name": k, **v} for k, v in sorted(dirs.items())],
            "totals": {"files": len(files),
                       "symbols": sum(d["symbols"] for d in dirs.values())},
            "hotspots": hs,
            "navigate": "summary(path='<dir|file>') → symbol(name) → context(symbol)"}
