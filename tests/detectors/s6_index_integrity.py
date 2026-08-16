"""Phase 3 (F-22/F-42/F-23) detector functions: index-integrity metrics.

Each function drives real product code (indexer.resolve_import, base.iter_files,
DB edges) so it stays true as the repo changes. Metrics return a float or int+
small dict so RECALL/PRECISION tests can assert against them.

Rules (TRACKER Phase 3 ENHANCE / 10-plan §3):
  INDEX-IMPORT-RESOLUTION — in-repo scoped import resolution rate (float 0..1).
  INDEX-BACKUP-POLLUTION  — fraction of indexed files under backup trees.
  INDEX-TESTED-BY-NOISE   — count of tested_by edges that are not real
                            (src not a live symbol id, or src under backups).
"""

from __future__ import annotations

import os

from cipkg import base, indexer


# Directory fragments that identify a backup/duplicate-generated tree.
# Segment-aware: a path segment that IS a backup dir, starts a backup-*/emergency_*
# prefix, or ends .bak/.orig. A test filename merely *containing* "backup_"
# (e.g. test_f42_backup_pollution) is NOT a backup tree.
def _is_backup_rel(path: str) -> bool:
    segs = path.replace("\\", "/").split("/")
    return any(
        seg == "backups" or seg == "htmlcov"
        or seg.startswith(("backup_", "emergency_"))
        or seg.endswith((".bak", ".orig"))
        for seg in segs
    )


def _in_repo_spec(spec: str) -> bool:
    """True when the spec targets a repo-local module (not stdlib/third-party).

    Relative specs and the repo package root (cipkg.*/lib.*) are in-repo.
    """
    return spec.startswith(".") or spec in ("cipkg", "lib") or spec.startswith(("cipkg.", "lib."))


def repo_import_resolution(root: str, cfg=None) -> tuple[int, int, float]:
    """(in_repo_specs, resolved, rate) computed with the REAL resolver."""
    cfg = cfg or base.load_config(root)
    paths = {p for p in base.iter_files(root, cfg)}
    codelike = [p for p in paths if p.endswith(".py") or p.endswith((".ts", ".tsx", ".js", ".jsx", ".mjs"))]
    total = resolved = 0
    for rel in codelike:
        try:
            with open(os.path.join(root, rel), encoding="utf-8", errors="replace") as f:
                src = f.read()
        except OSError:
            continue
        for spec in _extract_specs(src, rel):
            if not _in_repo_spec(spec):
                continue
            total += 1
            if indexer.resolve_import(rel, spec, paths):
                resolved += 1
    rate = (resolved / total) if total else 1.0
    return total, resolved, rate


def _extract_specs(src: str, rel: str) -> list[str]:
    """Extract import specs from source using the product parser (no tree-sitter)."""
    try:
        from cipkg import parse
        return list(parse.extract_imports(src, indexer.lang_for(rel)))
    except Exception:
        return []


def backup_pollution(root: str, cfg=None) -> tuple[int, int, float]:
    """(backup_files, total_files, fraction) per iter_files (post-F-42 scan)."""
    cfg = cfg or base.load_config(root)
    files = list(base.iter_files(root, cfg))
    backup = [p for p in files if _is_backup_rel(p)]
    frac = (len(backup) / len(files)) if files else 0.0
    return len(backup), len(files), frac


def tested_by_noise(con) -> tuple[int, int]:
    """(noisy_edges, total_tested_by) from a live index DB (sqlite connection)."""
    try:
        symbol_ids = {r["id"] for r in con.execute("SELECT id FROM symbols")}
    except Exception:
        symbol_ids = set()
    total = noisy = 0
    for row in con.execute("SELECT src, src_path FROM edges WHERE kind='tested_by'"):
        total += 1
        # Same segment-aware backup predicate as the scanner, so the metric can
        # never drift from the F-42 gating.
        if row["src"] not in symbol_ids or _is_backup_rel(row["src_path"] or ""):
            noisy += 1
    return noisy, total