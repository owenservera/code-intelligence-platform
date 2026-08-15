"""Vector store abstraction. Default: SQLite BLOBs with a cached numpy matrix
for O(1) repeated KNN. Optional sqlite-vec extension for >100k-chunk repos."""
import struct
from .store import vector_matrix


def knn(con, model, qv, k=30, backend="sqlite"):
    """Return [(score, chunk_id), ...] ranked by cosine similarity."""
    if backend == "sqlite-vec":
        try:
            return _knn_sqlite_vec(con, model, qv, k)
        except Exception:
            pass
    ids, mat = vector_matrix(con, model)
    if not ids:
        return []
    if isinstance(mat, list):   # numpy unavailable -> pure python fallback
        from .embed import from_blob, cosine
        scored = sorted(((cosine(qv, v), cid) for cid, v in zip(ids, mat)),
                        key=lambda x: -x[0])
        return scored[:k]
    import numpy as np
    scores = np.asarray(mat) @ np.asarray(qv, dtype=np.float32)
    top = scores.argsort()[::-1][:k]
    return [(float(scores[i]), ids[i]) for i in top]


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
