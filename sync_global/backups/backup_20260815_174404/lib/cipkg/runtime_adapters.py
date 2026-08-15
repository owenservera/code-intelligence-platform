"""Runtime signal adapters: vitest/jest JSON, pytest JUnit XML, tsc output, generic JSON.
Signals power `broken`, summaries, and reranking — the 'what is currently broken' layer."""
import json, os, re, sys, time
import xml.etree.ElementTree as ET
from .base import repo_root
from .store import connect

def _norm(path):
    return (path or "").replace(os.sep, "/").lstrip("./")

def _put(con, kind, path, name, symbol_id=None, payload=None):
    sid = f"sig:{kind}:{path}::{name}"
    con.execute("INSERT OR REPLACE INTO signals(id,kind,path,symbol_id,name,payload,ts) "
                "VALUES(?,?,?,?,?,?,?)",
                (sid, kind, path, symbol_id, name, json.dumps(payload or {}), time.time()))

def ingest_vitest(con, data):
    n = 0
    for tr in (data.get("testResults") or data.get("test_results") or []):
        f = _norm(tr.get("name") or tr.get("file"))
        for ar in (tr.get("assertionResults") or tr.get("assertion_results") or []):
            status = ar.get("status", "")
            kind = {"passed": "test_pass", "failed": "test_fail"}.get(status)
            if not kind: continue
            anc = ar.get("ancestorTitles") or []
            name = " > ".join(anc + [ar.get("title") or ar.get("fullName") or "?"])
            _put(con, kind, f, name, payload={"duration": ar.get("duration")})
            n += 1
    return n

def ingest_pytest(con, xml_path):
    n = 0
    for case in ET.parse(xml_path).getroot().iter("testcase"):
        f = _norm(case.get("file") or "")
        name = f'{case.get("classname", "")}.{case.get("name", "")}'
        failed = case.find("failure") is not None or case.find("error") is not None
        _put(con, "test_fail" if failed else "test_pass", f, name)
        n += 1
    return n

TSC_RE = re.compile(r"^([^(]+)\((\d+),(\d+)\):\s+error\s+(TS\d+):\s+(.*)$")

def ingest_tsc(con, text):
    n = 0
    for line in text.splitlines():
        m = TSC_RE.match(line.strip())
        if not m: continue
        f, ln, _col, code, msg = m.groups()
        f = _norm(f)
        sym = con.execute("SELECT id FROM symbols WHERE path=? AND start_line<=? AND end_line>=? "
                          "ORDER BY (end_line-start_line) LIMIT 1",
                          (f, int(ln), int(ln))).fetchone()
        _put(con, "type_error", f, f"{code} L{ln}",
             symbol_id=sym["id"] if sym else None,
             payload={"line": int(ln), "message": msg[:300]})
        n += 1
    return n

def ingest_generic(con, data):
    items = data if isinstance(data, list) else data.get("events", [])
    n = 0
    for i, ev in enumerate(items):
        kind = ev.get("kind", "custom")
        _put(con, kind, _norm(ev.get("path")), ev.get("name", f"event-{i}"),
             symbol_id=ev.get("symbol_id"), payload=ev.get("payload") or {})
        n += 1
    return n

def ingest(root, kind, file_path):
    root = root or repo_root(); con = connect(root)
    text = (sys.stdin.read() if file_path == "-"
            else open(file_path, encoding="utf-8", errors="replace").read())
    try:
        if kind in ("vitest", "jest"): n = ingest_vitest(con, json.loads(text))
        elif kind == "pytest":         n = ingest_pytest(con, file_path)
        elif kind == "tsc":            n = ingest_tsc(con, text)
        elif kind == "generic":        n = ingest_generic(con, json.loads(text))
        else: return {"error": f"unknown kind: {kind}"}
    except Exception as e:
        return {"error": f"parse failed: {e}"}
    con.execute("INSERT INTO events(ts,kind,payload) VALUES(?,?,?)",
                (time.time(), f"ingest:{kind}", str(n)))
    con.commit()
    return {"ingested": n, "kind": kind}

def broken(root=None, limit=30, window_days=14):
    root = root or repo_root(); con = connect(root)
    cutoff = time.time() - window_days * 86400
    rows = con.execute("SELECT kind, path, symbol_id, name, payload, ts FROM signals "
                       "WHERE kind IN ('test_fail','type_error') AND ts>=? "
                       "ORDER BY ts DESC LIMIT ?", (cutoff, limit)).fetchall()
    files = {}
    for r in rows:
        e = files.setdefault(r["path"], {"test_fail": 0, "type_error": 0})
        if r["kind"] in e: e[r["kind"]] += 1
    return {"window_days": window_days,
            "files": [{"path": p, **c} for p, c in sorted(
                files.items(), key=lambda kv: -(kv[1]["test_fail"] + kv[1]["type_error"]))],
            "signals": [dict(r) for r in rows]}
