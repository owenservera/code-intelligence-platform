"""Phase 3 regression tests: index-integrity detectors (F-22/F-42/F-23).

RUNBOOK §4 / TRACKER Phase 3 / 10-plan §3. Regression-locks three index
correctness fixes on the retail surface so every future sync stays clean:

F-22  INDEX-IMPORT-RESOLUTION — `resolve_import` must convert Python dotted
      specs into real repo paths. Pre-fix it naively joined (`lib/cipkg/.base.py`)
      so ~99.8% of in-repo relative imports failed to resolve (0/5276 effective).
      Locks: multi-segment (`stack.common` -> `stack/common`), parent hops
      (`..base` from `stack/` -> `cipkg/base.py`), and `cipkg.*` abs specs.
      Repo flip: in-repo rate >= 0.99 after fix (pre-fix 0.2%). Phase 0 fixed
      the final broken ref (`cli.py .ingest` -> `runtime_adapters`), so the repo
      now resolves 100% of in-repo specs (missed == empty set).

F-42  INDEX-BACKUP-POLLUTION — `iter_files` must never index backup/duplicate
      trees even when `index.exclude` is empty. Pre-fix 575/753 (76.4%) of the
      live index was sync_global backup copies. Locks: BACKUP_DIR_PREFIXES and
      DEFAULT_EXCLUDES skip them; repo fraction == 0.0 after fix; a synthetic
      tree with a `backup_*/` dir that the OLD scanner would have indexed now
      stays clean (flip).

F-23  INDEX-TESTED-BY-NOISE — tested_by edges must be grounded in the resolved
      import/call/reference graph, not name-mention chunk matching, and never
      reference backup symbols. Pre-fix: 4462 invented edges from backup-symbol
      srcs. Locks: a synthetic DB with (a) clean edges -> 0 noise, (b) edges
      whose src is missing / under backups -> the detector fires (RECALL).
"""

from __future__ import annotations

import pathlib
import sqlite3
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "lib"))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from cipkg import base  # noqa: E402
from cipkg import indexer  # noqa: E402
from s6_index_integrity import (  # noqa: E402
    _in_repo_spec,
    backup_pollution,
    repo_import_resolution,
    tested_by_noise,
)

REPO = str(ROOT)


def _paths_subset(root, *rels):
    return {str(p.relative_to(root)).replace("\\", "/") for p in
            (pathlib.Path(root) / r for r in rels)}


# ---------------------------------------------------------------------------
# F-22 — resolve_import unit semantics (RECALL vs the naive-join bug)
# ---------------------------------------------------------------------------

def test_f22_single_dot_relative_resolves_to_package_file():
    P = _paths_subset(REPO, "lib/cipkg/base.py", "lib/cipkg/session.py",
                      "lib/cipkg/__init__.py")
    assert indexer.resolve_import("lib/cipkg/session.py", ".base", P) == "lib/cipkg/base.py"


def test_f22_multi_segment_dots_are_package_separators():
    # `from .stack.common import` must resolve to stack/common.py, never a
    # literal ``lib/cipkg/stack.common.py`` artifact.
    P = _paths_subset(REPO, "lib/cipkg/dashboard.py", "lib/cipkg/stack/common.py",
                      "lib/cipkg/stack/__init__.py")
    got = indexer.resolve_import("lib/cipkg/dashboard.py", ".stack.common", P)
    assert got == "lib/cipkg/stack/common.py"
    assert "/.aggregated" not in got and "/.stack" not in got


def test_f22_multi_segment_memory_module_resolves():
    P = _paths_subset(REPO, "lib/cipkg/learning_system.py",
                      "lib/cipkg/memory/episodic.py",
                      "lib/cipkg/memory/temporal_graph.py")
    assert indexer.resolve_import("lib/cipkg/learning_system.py",
                                  ".memory.episodic", P) == "lib/cipkg/memory/episodic.py"
    assert indexer.resolve_import("lib/cipkg/learning_system.py",
                                  ".memory.temporal_graph", P) == "lib/cipkg/memory/temporal_graph.py"


def test_f22_dotdot_from_stack_hops_up_to_package():
    P = _paths_subset(REPO, "lib/cipkg/stack/audit.py", "lib/cipkg/base.py",
                      "lib/cipkg/store.py", "lib/cipkg/__init__.py")
    assert indexer.resolve_import("lib/cipkg/stack/audit.py", "..base", P) == "lib/cipkg/base.py"
    assert indexer.resolve_import("lib/cipkg/stack/audit.py", "..store", P) == "lib/cipkg/store.py"
    assert indexer.resolve_import("lib/cipkg/stack/audit.py", "..", P) == "lib/cipkg/__init__.py"


def test_f22_absolute_cipkg_spec_tries_roots():
    P = _paths_subset(REPO, "lib/cipkg/command_registry.py",
                      "lib/cipkg/web_server.py", "lib/cipkg/__init__.py")
    assert indexer.resolve_import("lib/cipkg/web_server.py",
                                  "cipkg.command_registry", P) == "lib/cipkg/command_registry.py"


def test_f22_missing_module_stays_none():
    # Genuine dead refs must stay unresolved (returns None), not fake-resolve.
    P = _paths_subset(REPO, "lib/cipkg/cli.py")
    assert indexer.resolve_import("lib/cipkg/cli.py", ".ingest", P) is None
    assert indexer.resolve_import("lib/cipkg/web_server.py", "cipkg.no_such_mod", P) is None


# ---------------------------------------------------------------------------
# F-22 — repo flip: in-repo resolution rate after the fix
# ---------------------------------------------------------------------------

def test_f22_repo_inrepo_resolution_rate_high():
    total, resolved, rate = repo_import_resolution(REPO)
    assert total >= 100            # real signal, not a vacuous pass
    assert rate >= 0.99            # pre-fix was ~0.2%


def test_f22_repo_sole_unresolved_is_known_broken_ref():
    cfg = base.load_config(REPO)
    paths = {p for p in base.iter_files(REPO, cfg)}
    from cipkg import parse  # noqa: PLC0415
    missed = set()
    for rel in [p for p in paths if p.endswith(".py")]:
        src = (pathlib.Path(REPO) / rel).read_text(encoding="utf-8", errors="replace")
        for spec in parse.extract_imports(src, indexer.lang_for(rel)):
            if _in_repo_spec(spec) and not indexer.resolve_import(rel, spec, paths):
                missed.add((rel, spec))
    # Phase 0 flip: the last known-broken ref (cli.py .ingest -> runtime_adapters)
    # is fixed, so the repo resolves 100% of in-repo specs.
    assert missed == set()


# ---------------------------------------------------------------------------
# F-42 — backup pollution (RECALL synthetic flip + repo zero + precision)
# ---------------------------------------------------------------------------

def test_f42_synthetic_backup_tree_stays_clean(even_with_empty_config_excludes):
    # The tree the OLD scanner indexed (backup copies under sync_global) now
    # must not be picked up by iter_files at all.
    root = pathlib.Path(even_with_empty_config_excludes)
    files = sorted(base.iter_files(str(root), base.load_config(str(root))))
    assert files == ["config.toml", "lib/cipkg/base.py"]


def test_f42_repo_has_zero_backup_pollution():
    backup, total, frac = backup_pollution(REPO)
    assert total > 50
    assert backup == 0 and frac == 0.0     # pre-fix: 575 / 753 (76.4%)


def test_f42_backup_fragment_detector_itself_fires():
    # Precision check on the metric: it must still COUNT backups when the path
    # set actually contains them (so a regression re-introducing backup files
    # will flip the repo test red).
    import s6_index_integrity as s6  # noqa: PLC0415
    backup_rel = "sync_global/backups/backup_20260815/emergency_base.py"
    assert s6._is_backup_rel(backup_rel) is True
    assert s6._is_backup_rel("lib/cipkg/base.py") is False
    # a test filename merely containing the word must NOT match (over-match bug)
    assert s6._is_backup_rel("tests/detectors/test_f42_backup_pollution.py") is False


def test_f42_gatekeeper_skips_backup_segments_and_explains():
    # THE ingestion surface: `iter_files_smart`/`_decide` must skip backup trees
    # even when git-tracked and `index.exclude` is empty, and `explain()` must
    # report the real reason instead of INDEX.
    from cipkg import gatekeeper  # noqa: PLC0415
    assert gatekeeper._is_backup_segment("backup_20260815") is True
    assert gatekeeper._is_backup_segment("emergency_base.py") is True
    assert gatekeeper._is_backup_segment("backups") is True
    assert gatekeeper._is_backup_segment("htmlcov") is True
    # over-match guard
    assert gatekeeper._is_backup_segment("test_f42_backup_pollution.py") is False
    assert gatekeeper._is_backup_segment("lib") is False
    tree = str(REPO)
    d, tier, why = gatekeeper._decide(
        "sync_global/backups/backup_20260815/emergency_base.py", "", 100,
        base.load_config(tree), set(["sync_global/backups/backup_20260815/emergency_base.py"]), None)
    assert d == "skip" and why == "backup/duplicate tree"
    # and the live scan yields zero backup-tracked files
    cfg = base.load_config(tree)
    rels = [rel for rel, _t, _w in gatekeeper.iter_files_smart(tree, cfg)]
    assert len(rels) > 50
    assert not any(gatekeeper._is_backup_segment(seg) for rel in rels for seg in rel.split("/"))


# ---------------------------------------------------------------------------
# F-23 — tested_by noise (RECALL on broken synthetic DB + precision on clean)
# ---------------------------------------------------------------------------

def _make_db(edges, symbols):
    con = sqlite3.connect(":memory:")
    con.row_factory = sqlite3.Row
    con.executescript("""
        CREATE TABLE symbols (id TEXT PRIMARY KEY, path TEXT);
        CREATE TABLE edges (src TEXT, dst TEXT, kind TEXT, src_path TEXT);
        """)
    con.executemany("INSERT INTO symbols VALUES(?,?)", symbols)
    con.executemany("INSERT INTO edges VALUES(?,?,?,?)", edges)
    return con


def test_f23_noise_detector_fires_on_broken_edges():
    # RECALL: the old heuristic emitted tested_by edges from backup-symbol
    # srcs (edge 1) and from src ids that no longer exist (edges 3, 5).
    con = _make_db(
        edges=[("python://sync_global/backups/bak/x.py#f", "tests/test_x.py", "tested_by",
                "sync_global/backups/bak/x.py"),
               ("python://lib/legacy.py#g", "tests/test_y.py", "tested_by", "lib/legacy.py"),
               ("python://lost.py#h", "tests/test_z.py", "tested_by", "tests/test_z.py"),
               ("python://lib/real.py#f", "tests/test_r.py", "tested_by", "lib/real.py"),
               ("python://deleted.py#k", "tests/test_w.py", "tested_by", "tests/test_w.py")],
        symbols=[("python://sync_global/backups/bak/x.py#f", "sync_global/backups/bak/x.py"),
                 ("python://lib/legacy.py#g", "lib/legacy.py"),
                 ("python://lib/real.py#f", "lib/real.py")])
    noisy, total = tested_by_noise(con)
    assert total == 5
    assert noisy == 3                       # 1 backup-src + 2 missing-src


def test_f23_noise_detector_silent_on_clean_edges():
    # PRECISION: real tested_by edges (src in symbols, non-backup paths) → 0.
    con = _make_db(
        edges=[("python://lib/cipkg/store.py#connect", "tests/test_store.py", "tested_by",
                "lib/cipkg/store.py"),
               ("python://lib/cipkg/base.py#load_config", "tests/test_base.py", "tested_by",
                "lib/cipkg/base.py")],
        symbols=[("python://lib/cipkg/store.py#connect", "lib/cipkg/store.py"),
                 ("python://lib/cipkg/base.py#load_config", "lib/cipkg/base.py")])
    noisy, total = tested_by_noise(con)
    assert total == 2
    assert noisy == 0


# ---------------------------------------------------------------------------
# fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def even_with_empty_config_excludes(tmp_path):
    """A repo with explicit empty excludes — the case F-42 had to harden."""
    cfg = tmp_path / "config.toml"
    cfg.write_text('[index]\nexclude = []\n', encoding="utf-8")
    lib = tmp_path / "lib" / "cipkg"
    lib.mkdir(parents=True)
    (lib / "base.py").write_text("def f():\n    pass\n", encoding="utf-8")
    backup = tmp_path / "sync_global" / "backups" / "backup_20260815"
    backup.mkdir(parents=True)
    (backup / "emergency_base.py").write_text("def stale():\n    pass\n", encoding="utf-8")
    htmlcov = tmp_path / "htmlcov"
    htmlcov.mkdir()
    (htmlcov / "index.html").write_text("<html>cov</html>", encoding="utf-8")
    return tmp_path