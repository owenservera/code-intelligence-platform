"""Blast-radius analysis: transitive dependents, affected routes, tests to run,
risk level — for a file, a symbol, or an entire git diff (PR mode)."""
import subprocess
from ..base import repo_root
from ..store import connect
from .common import ensure

def _to_file(con, node):
    if "://" in node:
        r = con.execute("SELECT path FROM symbols WHERE id=?", (node,)).fetchone()
        return r["path"] if r else None
    return node

def _dependents(con, seed_files, depth=2):
    frontier, seen = set(seed_files), set(seed_files)
    for _ in range(max(1, min(depth, 3))):
        nxt = set()
        for f in frontier:
            for r in con.execute(
                    "SELECT src FROM edges WHERE dst=? AND kind IN ('imports','calls','references')",
                    (f,)):
                p = _to_file(con, r["src"])
                if p and p not in seen:
                    seen.add(p); nxt.add(p)
        frontier = nxt
    return seen

def impact(root=None, target="", depth=2):
    root = root or repo_root(); con = connect(root); ensure(con)
    seed = set()
    if con.execute("SELECT 1 FROM files WHERE path=?", (target,)).fetchone():
        seed.add(target)
    else:
        sym = con.execute("SELECT path FROM symbols WHERE id=? OR name=? LIMIT 1",
                          (target, target)).fetchone()
        if sym: seed.add(sym["path"])
    if not seed:
        return {"error": f"unknown target: {target}"}
    dep = _dependents(con, seed, depth)
    tests = set()
    for r in con.execute("SELECT src, dst FROM edges WHERE kind='tested_by'"):
        s = con.execute("SELECT path FROM symbols WHERE id=?", (r["src"],)).fetchone()
        if s and s["path"] in dep:
            tests.add(r["dst"])
    ph = ",".join("?" * len(dep))
    routes_hit = [dict(r) for r in con.execute(
        f"SELECT path, kind FROM routes WHERE file IN ({ph})", list(dep))]
    findings_hit = con.execute(
        f"SELECT COUNT(*) c FROM findings WHERE status='open' AND path IN ({ph})",
        list(dep)).fetchone()["c"]
    try:
        from ..gitindex import hotspots
        hs = {h["path"]: h["score"] for h in hotspots(root, k=50)}
        heat = max((hs.get(p, 0.0) for p in dep), default=0.0)
    except Exception:
        heat = 0.0
    risk = "low"
    if routes_hit or len(dep) > 8 or findings_hit > 3: risk = "medium"
    if len(dep) > 20 or (routes_hit and heat > 2): risk = "high"
    advice = []
    if risk == "high":
        advice.append("High blast radius: land in small increments; full test pass required.")
    if routes_hit:
        advice.append(f"{len(routes_hit)} route(s) affected — verify API contracts and consumers.")
    if tests:
        advice.append("Run the listed tests before merging.")
    else:
        advice.append("No tests cover this area — add one test for the changed behavior first.")
    return {"target": target, "risk": risk,
            "seed_files": sorted(seed),
            "affected_files": sorted(dep)[:50], "affected_count": len(dep),
            "tests_to_run": sorted(tests)[:20],
            "routes_affected": routes_hit[:10],
            "open_findings_in_area": findings_hit,
            "hotspot_heat": round(heat, 1), "advice": advice}

def impact_diff(root=None, ref="HEAD"):
    root = root or repo_root()
    try:
        out = subprocess.run(["git", "diff", "--name-only", ref],
                             cwd=root, capture_output=True, text=True, timeout=30)
    except Exception as e:
        return {"error": str(e)}
    files = [l.strip() for l in out.stdout.splitlines() if l.strip()]
    union, all_tests, all_routes, worst = set(), set(), [], "low"
    order = {"low": 0, "medium": 1, "high": 2}
    for f in files[:20]:
        r = impact(root, f)
        if "error" in r: continue
        union.update(r["affected_files"])
        all_tests.update(r["tests_to_run"])
        all_routes += r["routes_affected"]
        if order[r["risk"]] > order[worst]: worst = r["risk"]
    return {"base": ref, "changed_files": files,
            "risk": worst, "affected_count": len(union),
            "affected_files": sorted(union)[:60],
            "tests_to_run": sorted(all_tests)[:25],
            "routes_affected": all_routes[:10]}
