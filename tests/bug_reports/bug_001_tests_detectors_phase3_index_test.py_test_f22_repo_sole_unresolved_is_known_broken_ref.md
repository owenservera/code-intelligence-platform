# Bug Report #1

## Bug Report: tests/detectors/phase3_index_test.py::test_f22_repo_sole_unresolved_is_known_broken_ref

Severity: HIGH  
Detected: 2026-08-16T16:50:22.002613  
Error Type: failed

### Error Message
```
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
>       assert missed == {("lib/cipkg/cli.py", ".ingest")}
E       AssertionError: assert set() == {('lib/cipkg/...', '.ingest')}
E         
E         Extra items in the right set:
E         ('lib/cipkg/cli.py', '.ingest')
E         Use -v to get more diff

tests\detectors\phase3_index_test.py:129: AssertionError
```

### Traceback
```
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
>       assert missed == {("lib/cipkg/cli.py", ".ingest")}
E       AssertionError: assert set() == {('lib/cipkg/...', '.ingest')}
E         
E         Extra items in the right set:
E         ('lib/cipkg/cli.py', '.ingest')
E         Use -v to get more diff

tests\detectors\phase3_index_test.py:129: AssertionError
```

### Suggested Fix
BUG: Test assertion failed - actual behavior doesn't match expectations. Review the test expectations and adjust either the test or the implementation.

---
