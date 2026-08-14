"""Git history index: commits → modified_by edges, co_change edges, hotspot scores.
Answers 'what recently changed' and 'what changes together'."""
import subprocess, time
from collections import Counter
from .base import repo_root
from .store import connect

def git_index(root=None, depth=500, co_change_min=2):
    root = root or repo_root()
    con = connect(root)
    try:
        out = subprocess.run(
            ["git", "log", "--pretty=format:@CIP@%H%x00%at%x00%an%x00%s",
             "--name-only", "-n", str(depth)],
            cwd=root, capture_output=True, text=True, timeout=180)
    except Exception as e:
        return {"error": str(e)}
    if out.returncode != 0:
        return {"error": out.stderr.strip() or "git log failed"}
    commits, cur = [], None
    for line in out.stdout.splitlines():
        if line.startswith("@CIP@"):
            if cur: commits.append(cur)
            sha_, ts, author, msg = line[5:].split("\x00", 3)
            cur = {"sha": sha_, "ts": float(ts), "author": author, "msg": msg, "files": []}
        elif line.strip() and cur:
            cur["files"].append(line.strip())
    if cur: commits.append(cur)

    con.execute("DELETE FROM commits")
    con.execute("DELETE FROM commit_files")
    con.execute("DELETE FROM edges WHERE kind IN ('modified_by','co_change')")
    for c in commits:
        con.execute("INSERT OR REPLACE INTO commits(sha,ts,author,message,files_changed) "
                    "VALUES(?,?,?,?,?)",
                    (c["sha"], c["ts"], c["author"], c["msg"], len(c["files"])))
        for f in c["files"]:
            con.execute("INSERT OR IGNORE INTO commit_files(sha,path) VALUES(?,?)", (c["sha"], f))
    for c in commits[:50]:                       # modified_by for recent history
        for f in c["files"]:
            con.execute("INSERT OR IGNORE INTO edges(src,dst,kind,src_path) VALUES(?,?,?,?)",
                        (f, c["sha"], "modified_by", f))
    pairs = Counter()                            # co-change pairs
    for c in commits:
        fs = sorted(set(c["files"]))
        for i in range(len(fs)):
            for j in range(i + 1, min(len(fs), i + 12)):
                pairs[(fs[i], fs[j])] += 1
    added = 0
    for (a, b), n in pairs.most_common(500):
        if n < co_change_min: break
        con.execute("INSERT OR IGNORE INTO edges(src,dst,kind,src_path) VALUES(?,?,?,?)",
                    (a, b, "co_change", a))
        added += 1
    con.commit()
    return {"commits": len(commits), "co_change_edges": added}

def hotspots(root=None, k=15):
    root = root or repo_root(); con = connect(root)
    now = time.time()
    rows = con.execute("SELECT cf.path, c.ts FROM commit_files cf "
                       "JOIN commits c ON c.sha=cf.sha").fetchall()
    scores = {}
    for r in rows:
        age_days = max(0.0, (now - r["ts"]) / 86400.0)
        w = 1.0 if age_days <= 30 else (0.5 if age_days <= 90 else 0.15)
        scores[r["path"]] = scores.get(r["path"], 0.0) + w
    return [{"path": p, "score": round(s, 1)}
            for p, s in sorted(scores.items(), key=lambda kv: -kv[1])[:k]]
