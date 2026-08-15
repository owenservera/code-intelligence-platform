# Root cause — and the fix

Right now every `cip` invocation (search, sync, git hook, MCP tool) is a **fresh Python process** that cold-loads a 130MB model + PyTorch from disk, uses it once, and dies. On the 3700U that's ~8–15s of boot every time. The model is never kept resident.

**The fix: keep ONE warm model in a resident process, and make everything else a thin client of it.**

```
BEFORE:  cip search ──▶ new process ──▶ LOAD MODEL (10s) ──▶ embed ──▶ die
         git hook   ──▶ new process ──▶ LOAD MODEL (10s) ──▶ embed ──▶ die
         MCP tool   ──▶ reload per call...

AFTER:   cip daemon ══▶ MODEL RESIDENT IN RAM (loaded once, ~10s, at boot)
              ▲  ▲  ▲
              │  │  └── git hooks / cip sync  ──▶ HTTP /embed  (~5ms)
              │  └───── cip search / context  ──▶ HTTP /embed  (~5ms)
              └──────── MCP / dashboard       ──▶ HTTP /embed  (~5ms)
                          (fallback: in-process singleton if daemon is down)
```

---

## 1. `lib/cipkg/embed.py` — REPLACE entirely

```python
"""
CIP Embedding Engine — warm-model architecture.
Tier 1: EMBEDDING SERVICE — resident daemon holds the model; all processes call
        it over localhost HTTP. Zero boot per call.
Tier 2: IN-PROCESS SINGLETON — model loaded once per process, memoized (fallback).
"""
import json, os, subprocess, sys, time, urllib.request

MODEL_NAME = "BAAI/bge-small-en-v1.5"
DEVICE = "cpu"
THREADS = 4                     # physical cores on Ryzen 3700U

_EMBEDDER_CACHE = {}            # (kind, key) -> instance, per-process memoization

def _cached(key, build):
    if key not in _EMBEDDER_CACHE:
        _EMBEDDER_CACHE[key] = build()
    return _EMBEDDER_CACHE[key]

# ---------------- Tier 1: warm service client ----------------

class RemoteEmbedder:
    """Thin client for the model living inside `cip daemon` / `cip serve`."""
    def __init__(self, port, name=None, dim=384):
        self.port = port
        self.name = name or f"service:{MODEL_NAME}"
        self.dim = dim
    def embed(self, texts):
        if not texts: return []
        req = urllib.request.Request(
            f"http://127.0.0.1:{self.port}/embed",
            data=json.dumps({"texts": texts}).encode(),
            headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=120) as r:
            return json.load(r)["vectors"]

def service_health(port, timeout=0.35):
    try:
        with urllib.request.urlopen(
                f"http://127.0.0.1:{port}/embed/health", timeout=timeout) as r:
            return json.load(r)
    except Exception:
        return None

def _start_service(port):
    """Detached daemon spawn (Windows + POSIX), then wait until warm."""
    kw = dict(stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
              stdin=subprocess.DEVNULL)
    try:
        if sys.platform == "win32":
            kw["creationflags"] = 0x08000000 | 0x00000200   # no window + new group
            subprocess.Popen(["cmd", "/c", "cip", "daemon", "--port", str(port)], **kw)
        else:
            kw["start_new_session"] = True
            subprocess.Popen(["cip", "daemon", "--port", str(port)], **kw)
    except Exception:
        return False
    deadline = time.time() + 120            # cold boot includes the model load
    while time.time() < deadline:
        h = service_health(port, timeout=1.0)
        if h and h.get("warm"):
            return True
        time.sleep(1.0)
    return False

# ---------------- Tier 2: local engine ----------------

class LocalEmbedder:
    def __init__(self, model_name=MODEL_NAME):
        import torch
        from sentence_transformers import SentenceTransformer
        self.name = f"local:{model_name}"
        self.dim = 384
        torch.set_num_threads(THREADS)
        cache_dir = os.path.join(os.path.expanduser("~"), ".cache", "huggingface", "hub")
        t0 = time.time()
        self.model = SentenceTransformer(model_name, device=DEVICE,
                                         cache_folder=cache_dir, trust_remote_code=False)
        self.load_ms = int((time.time() - t0) * 1000)
        print(f"cip: model loaded in {self.load_ms}ms ({self.name})")
    def embed(self, texts):
        if not texts: return []
        em = self.model.encode(texts, batch_size=32, show_progress_bar=False,
                               convert_to_tensor=True, normalize_embeddings=True)
        return em.cpu().numpy().tolist()

class HashingEmbedder:
    """Zero-dependency offline fallback."""
    def __init__(self, dim=1024):
        import hashlib as _h
        self._h, self.dim, self.name = _h, dim, f"hash-{dim}"
    def embed(self, texts):
        import math
        from .base import tokenize
        out = []
        for t in texts:
            v = [0.0] * self.dim
            for i, tok in enumerate(tokenize(t)):
                h = int(self._h.md5(tok.encode()).hexdigest(), 16)
                v[h % self.dim] += (1.0 if (h >> 120) % 2 == 0 else -1.0) * (1.0 + 1.0 / (1 + i))
            n = math.sqrt(sum(x * x for x in v)) or 1.0
            out.append([x / n for x in v])
        return out

def build_local_embedder(cfg):
    """Direct local build (used by daemon/serve — never goes through the service path)."""
    ecfg = cfg.get("embed", {})
    if ecfg.get("backend") == "hashing":
        return HashingEmbedder(int(ecfg.get("dim", 1024)))
    return LocalEmbedder(ecfg.get("model", MODEL_NAME))

# ---------------- resolution ----------------

def get_embedder(cfg, root=None):
    """Priority: warm service → auto-start service → in-process local singleton."""
    ecfg = cfg.get("embed", {})
    backend = ecfg.get("backend", "auto")
    port = int(ecfg.get("service_port", cfg.get("serve", {}).get("port", 8787)))

    if backend in ("auto", "service"):
        h = service_health(port)
        if h and h.get("warm"):
            return _cached(("service", port), lambda: RemoteEmbedder(
                port, name=h.get("model"), dim=int(h.get("dim") or 384)))

    if backend == "service" or (backend == "auto" and ecfg.get("autostart", True)):
        if backend != "hashing" and _start_service(port):
            h = service_health(port) or {}
            return _cached(("service", port), lambda: RemoteEmbedder(
                port, name=h.get("model"), dim=int(h.get("dim") or 384)))

    if backend == "hashing":
        return _cached(("hashing", 0), lambda: HashingEmbedder(int(ecfg.get("dim", 1024))))

    model = ecfg.get("model", MODEL_NAME)
    return _cached(("local", model), lambda: LocalEmbedder(model))

# ---------------- vector plumbing (unchanged contract) ----------------

import struct
def to_blob(v):   return struct.pack(f"<{len(v)}f", *v)
def from_blob(b): return struct.unpack(f"<{len(b)//4}f", b)
def cosine(a, b): return sum(x * y for x, y in zip(a, b))
```

## 2. `server.py` — add the `/embed` endpoints + pre-warm

**Patch A** — inside `serve()`, immediately after `cfg = load_config(root)` / `port = ...`:

```python
    from . import embed as E
    SERVE_STATE = {}
    print("cip: pre-warming embedding model…")
    _t = time.time()
    SERVE_STATE["emb"] = E._cached(("local", cfg["embed"].get("model", E.MODEL_NAME)),
                                   lambda: E.build_local_embedder(cfg))
    SERVE_STATE["t0"] = time.time()
    print(f"cip: model WARM in {int((time.time()-_t)*1000)}ms — holding resident")
```

**Patch B** — in `do_GET`, add before the `else` 404:

```python
            elif self.path == "/embed/health":
                emb = SERVE_STATE.get("emb")
                return self._send({"warm": emb is not None,
                                   "model": getattr(emb, "name", None),
                                   "dim": getattr(emb, "dim", None),
                                   "pid": os.getpid(),
                                   "uptime_s": round(time.time() - SERVE_STATE.get("t0", time.time()), 1)})
```

**Patch C** — in `do_POST`, at the top of the method (before the JSON-RPC dispatch):

```python
        if self.path == "/embed":
            n = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(n) or b"{}")
            emb = SERVE_STATE["emb"]
            vecs = emb.embed(body.get("texts", []))
            return self._send({"vectors": vecs, "model": emb.name,
                               "dim": emb.dim, "n": len(vecs)})
```

Since `daemon.py` runs `serve()`, the daemon gets all of this for free.

## 3. `mcp_stdio` — pre-warm at session start

Add at the top of `mcp_stdio()` (so the first agent query is instant, and it attaches to the daemon if one is running instead of loading locally):

```python
    import threading
    from .embed import get_embedder
    threading.Thread(target=lambda: get_embedder(cfg, root), daemon=True).start()
```

## 4. Config — append to `[embed]` in `~/.cip-global/templates/config.toml`

```toml
[embed]
backend = "auto"          # auto | service | local | hashing
model = "BAAI/bge-small-en-v1.5"
dim = 384
service_port = 8787       # where the warm model lives
autostart = true          # launch the daemon automatically if it's down
```

## 5. Diagnostic command — `cli.py` patch

Parser:

```python
    sub.add_parser("embedder", help="embedding engine status + benchmark")
```

Dispatch:

```python
    elif a.cmd == "embedder":
        from .embed import get_embedder, service_health
        cfg = load_config(root)
        port = int(cfg.get("serve", {}).get("port", 8787))
        h = service_health(port)
        print(f"service :{port}   ->  " +
              (f"WARM  model={h.get('model')}  uptime={h.get('uptime_s')}s" if h else "not running"))
        t0 = time.time()
        emb = get_embedder(cfg, root)
        print(f"active engine    ->  {emb.name}  (resolved in {int((time.time()-t0)*1000)}ms)")
        t0 = time.time()
        v = emb.embed(["benchmark: token refresh pipeline"])
        print(f"single embed     ->  {int((time.time()-t0)*1000)}ms  dim={len(v[0])}")
```

---

## 6. Setup & verification

```powershell
# 1. Start the warm model once (stays resident; survives terminal close)
cip daemon

# 2. Verify from ANY other terminal:
cip embedder
#   service :8787   ->  WARM  model=local:BAAI/bge-small-en-v1.5  uptime=42.7s
#   active engine   ->  service:local:BAAI/...  (resolved in 3ms)
#   single embed    ->  9ms  dim=384

# 3. (Optional) launch the daemon automatically at Windows login:
Set-Content "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup\cip-daemon.bat" "@echo off`r`ncip daemon"
```

## 7. What changes in practice

| Operation | Before | After |
|---|---|---|
| `cip search "..."` | ~10s (cold load) | **~10–30ms** |
| git hook `cip sync` (with changes) | ~10s+ | **~20–100ms** |
| MCP `search`/`context` tool | reload per call | **~10–30ms** |
| First call after machine boot | ~10s | ~10s **once** (daemon warms up), then instant |
| Daemon not running + `autostart=true` | — | auto-spawns, warms, continues — self-healing |

Three behaviors worth knowing: **everything falls back gracefully** — if the daemon is down and autostart is off, each process loads the model once and memoizes it (so long-lived processes like the MCP session or watcher never reload); the daemon has a lockfile so it can't double-start; and `backend = "hashing"` still gives you a fully-offline zero-model mode.
