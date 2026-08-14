"""
CIP v1.1 Local Embedding Engine
Hardware Target: AMD Ryzen 7 PRO 3700U (CPU-only)
Model: BAAI/bge-small-en-v1.5 (384-dim, 33M params)
"""
import hashlib, math, os, struct, torch
from sentence_transformers import SentenceTransformer

MODEL_NAME = "BAAI/bge-small-en-v1.5"
DEVICE = "cpu"
THREADS = 4

class LocalEmbedder:
    def __init__(self, root=None):
        self.name = f"local:{MODEL_NAME}"
        self.dim = 384
        self.cache_dir = os.path.join(os.path.expanduser("~"), ".cache", "huggingface", "hub")
        torch.set_num_threads(THREADS)
        print(f"cip: loading local embedding model '{MODEL_NAME}' (CPU, {THREADS} threads)...")
        self.model = SentenceTransformer(
            MODEL_NAME,
            device=DEVICE,
            cache_folder=self.cache_dir,
            trust_remote_code=False
        )
        print(f"cip: local embedder ready ({self.dim}d)")

    def embed(self, texts):
        if not texts:
            return []
        embeddings = self.model.encode(
            texts,
            batch_size=32,
            show_progress_bar=False,
            convert_to_tensor=True,
            normalize_embeddings=True
        )
        return embeddings.cpu().numpy().tolist()


class HashingEmbedder:
    """Signed feature-hashing of identifier tokens. Offline, deterministic, free."""
    def __init__(self, dim=1024):
        self.dim = dim
        self.name = f"hash-{dim}"
    def embed(self, texts):
        from .base import tokenize
        out = []
        for t in texts:
            v = [0.0] * self.dim
            for i, tok in enumerate(tokenize(t)):
                h = int(hashlib.md5(tok.encode()).hexdigest(), 16)
                sign = 1.0 if (h >> 120) % 2 == 0 else -1.0
                v[h % self.dim] += sign * (1.0 + 1.0 / (1 + i))
            n = math.sqrt(sum(x * x for x in v)) or 1.0
            out.append([x / n for x in v])
        return out


def get_embedder(cfg, root=None):
    backend = cfg.get("embed", {}).get("backend", "auto")
    if backend in ("local", "auto"):
        try:
            return LocalEmbedder(root)
        except Exception:
            if backend == "local": raise
            return HashingEmbedder(int(cfg["embed"].get("dim", 1024)))
    elif backend == "hashing":
        return HashingEmbedder(int(cfg["embed"].get("dim", 1024)))
    elif backend == "sentence-transformers":
        model = cfg["embed"].get("model", "all-MiniLM-L6-v2")
        from sentence_transformers import SentenceTransformer
        m = SentenceTransformer(model)
        class _ST:
            def __init__(self, model, m):
                self.name = f"st:{model}"
                self.dim = m.get_sentence_embedding_dimension()
                self.m = m
            def embed(self, texts):
                return [list(map(float, v)) for v in
                        self.m.encode(texts, normalize_embeddings=True)]
        return _ST(model, m)
    else:
        raise ValueError(f"Unknown embed backend '{backend}'. Use 'local', 'hashing', or 'auto'.")


def to_blob(v):   return struct.pack(f"<{len(v)}f", *v)
def from_blob(b): return struct.unpack(f"<{len(b)//4}f", b)
def cosine(a, b): return sum(x * y for x, y in zip(a, b))
