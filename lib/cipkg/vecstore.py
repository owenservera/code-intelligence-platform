"""Vector store abstraction. Default: SQLite BLOBs with numpy-accelerated cosine
when available. Optional sqlite-vec extension for >100k-chunk repos."""
import struct

def knn(con, model, qv, k=30, backend="sqlite"):
    if backend == "sqlite-vec":
        try:
            return _knn_sqlite_vec(con, model, qv, k)
        except Exception:
            pass
    rows = con.execute("SELECT id, vec FROM vectors WHERE model=?", (model,)).fetchall()
    if not rows: return []
    try:
        import numpy as np
        from .embed import from_blob
        ids = [r["id"] for r in rows]
        mat = np.array([from_blob(r["vec"]) for r in rows], dtype=np.float32)
        scores = mat @ np.asarray(qv, dtype=np.float32)
        top = scores.argsort()[::-1][:k]
        return [(float(scores[i]), ids[i]) for i in top]
    except ImportError:
        from .embed import from_blob, cosine
        scored = sorted(((cosine(qv, from_blob(r["vec"])), r["id"]) for r in rows),
                        key=lambda x: -x[0])
        return scored[:k]

def _knn_sqlite_vec(con, model, qv, k):
    """Experimental: requires the sqlite-vec extension and a populated
    vec_vectors(id, model, embedding) vec0 table. Falls back on any error."""
    con.enable_load_extension(True)
    con.load_extension("vec0")
    blob = struct.pack(f"<{len(qv)}f", *qv)
    rows = con.execute(
        "SELECT id, distance FROM vec_vectors WHERE embedding MATCH ? AND model=? "
        "ORDER BY distance LIMIT ?", (blob, model, k)).fetchall()
    return [(1.0 / (1.0 + r["distance"]), r["id"]) for r in rows]
