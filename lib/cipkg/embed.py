"""
CIP Embedding Engine — warm-model architecture.

Resolution order (get_embedder):
  1. Daemon warm?  -> RemoteEmbedder (zero-cost HTTP)
  2. Otherwise     -> LocalEmbedder (in-process singleton, ~10s first call)

Daemon is started EXPLICITLY via `cip daemon`.  get_embedder NEVER autostarts.
"""
import json, os, sys, time, urllib.request

MODEL_NAME = "BAAI/bge-small-en-v1.5"
DEVICE = "cpu"
THREADS = 4

_EMBEDDER_CACHE = {}

def _cached(key, build):
    if key not in _EMBEDDER_CACHE:
        _EMBEDDER_CACHE[key] = build()
    return _EMBEDDER_CACHE[key]

# ── Tier 1: warm service client ─────────────────────────────────────────────

class RemoteEmbedder:
    """Thin HTTP client for the model inside `cip daemon`."""
    def __init__(self, port, name=None, dim=384):
        self.port = port
        self.name = name or ("service:" + MODEL_NAME)
        self.dim = dim

    def embed(self, texts):
        if not texts:
            return []
        body = json.dumps({"texts": texts}).encode()
        req = urllib.request.Request(
            "http://127.0.0.1:%d/embed" % self.port,
            data=body,
            headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=120) as r:
            return json.load(r)["vectors"]


def service_health(port, timeout=0.5):
    """Check if daemon is warm.  Returns dict or None."""
    try:
        req = urllib.request.Request(
            "http://127.0.0.1:%d/embed/health" % port)
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.load(r)
    except Exception:
        return None


def find_daemon_port(root=None):
    """Find daemon port from cip_dir/port file, then check health."""
    from .base import data_dir, load_config
    try:
        cfg = load_config(root)
    except Exception:
        cfg = {}
    port = int(cfg.get("serve", {}).get("port", 8787))

    # check port file first (authoritative)
    if root:
        pf = os.path.join(data_dir(root), "daemon.port")
        if os.path.exists(pf):
            try:
                port = int(open(pf).read().strip())
            except Exception:
                pass

    h = service_health(port)
    if h and h.get("warm"):
        return port, h
    return None, None

# ── Tier 2: local engine ────────────────────────────────────────────────────

class LocalEmbedder:
    def __init__(self, model_name=MODEL_NAME):
        import os as _os
        # prevent HuggingFace Hub check for cached local models
        _os.environ["HF_HUB_OFFLINE"] = "1"
        import torch
        from sentence_transformers import SentenceTransformer
        self.name = "local:" + model_name
        self.dim = 384
        torch.set_num_threads(THREADS)
        cache_dir = _os.path.join(_os.path.expanduser("~"),
                                  ".cache", "huggingface", "hub")
        t0 = time.time()
        self.model = SentenceTransformer(
            model_name, device=DEVICE,
            cache_folder=cache_dir, trust_remote_code=False)
        self.load_ms = int((time.time() - t0) * 1000)

    def embed(self, texts):
        if not texts:
            return []
        em = self.model.encode(
            texts, batch_size=32, show_progress_bar=False,
            convert_to_tensor=True, normalize_embeddings=True)
        return em.cpu().numpy().tolist()


class HashingEmbedder:
    """Zero-dependency offline fallback."""
    def __init__(self, dim=1024):
        import hashlib as _h
        self._h, self.dim, self.name = _h, dim, "hash-" + str(dim)

    def embed(self, texts):
        import math
        from .base import tokenize
        out = []
        for t in texts:
            v = [0.0] * self.dim
            for i, tok in enumerate(tokenize(t)):
                h = int(self._h.md5(tok.encode()).hexdigest(), 16)
                v[h % self.dim] += (
                    (1.0 if (h >> 120) % 2 == 0 else -1.0)
                    * (1.0 + 1.0 / (1 + i)))
            n = math.sqrt(sum(x * x for x in v)) or 1.0
            out.append([x / n for x in v])
        return out


def build_local_embedder(cfg):
    """Direct local build (used by daemon/serve)."""
    ecfg = cfg.get("embed", {})
    if ecfg.get("backend") == "hashing":
        return HashingEmbedder(int(ecfg.get("dim", 1024)))
    return LocalEmbedder(ecfg.get("model", MODEL_NAME))

# ── resolution ───────────────────────────────────────────────────────────────

def _start_service(port):
    """Detached daemon spawn (Windows + POSIX), then wait until warm."""
    import subprocess
    kw = dict(stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
              stdin=subprocess.DEVNULL)
    try:
        if sys.platform == "win32":
            kw["creationflags"] = 0x08000000 | 0x00000200   # no window + new group
            subprocess.Popen(["cip", "daemon", "--port", str(port)], **kw)
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

def get_embedder(cfg, root=None):
    """
    Priority: warm daemon -> auto-start daemon -> hashing (offline) -> local (with warning).
    Always tells the user what's happening.
    """
    ecfg = cfg.get("embed", {})
    backend = ecfg.get("backend", "auto")
    port = int(ecfg.get("service_port", cfg.get("serve", {}).get("port", 8787)))

    # 1. try daemon (instant, zero-cost)
    if backend in ("auto", "service"):
        h = service_health(port)
        if h and h.get("warm"):
            return _cached(("service", port), lambda: RemoteEmbedder(
                port, name=h.get("model"), dim=int(h.get("dim") or 384)))

    # 2. auto-start daemon if configured
    if backend == "service" or (backend == "auto" and ecfg.get("autostart", True)):
        if backend != "hashing" and _start_service(port):
            h = service_health(port) or {}
            return _cached(("service", port), lambda: RemoteEmbedder(
                port, name=h.get("model"), dim=int(h.get("dim") or 384)))

    # 3. hashing (offline, no model needed)
    if backend == "hashing":
        return _cached(("hashing", 0), lambda: HashingEmbedder(
            int(ecfg.get("dim", 1024))))

    # 4. local singleton (slow, uses HF if not cached)
    model = ecfg.get("model", MODEL_NAME)
    return _cached(("local", model), lambda: LocalEmbedder(model))


def get_embedder_with_feedback(cfg, root=None):
    """Same as get_embedder but prints which path was taken."""
    ecfg = cfg.get("embed", {})
    backend = ecfg.get("backend", "auto")
    port = int(ecfg.get("service_port", cfg.get("serve", {}).get("port", 8787)))

    if backend in ("auto", "service"):
        h = service_health(port)
        if h and h.get("warm"):
            emb = _cached(("service", port), lambda: RemoteEmbedder(
                port, name=h.get("model"), dim=int(h.get("dim") or 384)))
            print("  daemon :%d warm  -> %s" % (port, emb.name))
            return emb
        # Auto-start if configured
        if backend == "service" or (backend == "auto" and ecfg.get("autostart", True)):
            print("  daemon :%d not running, auto-starting..." % port)
            if _start_service(port):
                h = service_health(port) or {}
                emb = _cached(("service", port), lambda: RemoteEmbedder(
                    port, name=h.get("model"), dim=int(h.get("dim") or 384)))
                print("  daemon :%d warm  -> %s" % (port, emb.name))
                return emb
            print("  daemon :%d failed to start" % port)
        else:
            print("  daemon :%d not running (start with: cip daemon)" % port)

    if backend == "hashing":
        emb = _cached(("hashing", 0), lambda: HashingEmbedder(
            int(ecfg.get("dim", 1024))))
        print("  offline -> %s (no daemon, using hashing fallback)" % emb.name)
        return emb

    model = ecfg.get("model", MODEL_NAME)
    emb = _cached(("local", model), lambda: LocalEmbedder(model))
    print("  local   -> %s (%dms load)" % (emb.name, getattr(emb, "load_ms", 0)))
    return emb

# ── vector plumbing ──────────────────────────────────────────────────────────

import struct
def to_blob(v):   return struct.pack("<%df" % len(v), *v)
def from_blob(b): return struct.unpack("<%df" % (len(b) // 4), b)
def cosine(a, b): return sum(x * y for x, y in zip(a, b))
