# PROFILE — CIP's own dogfooding configuration

**Framework:** `RUNBOOK.md` §0 (what the campaign is) · **Instance:** CIP itself (Python, `lib/cipkg/`)
**Date:** 2026-08-16

CIP is a **general, polyglot code-indexing + issue-detection SYSTEM** — one product run
against any repo, any language, now and for all future repos. This file records CIP's OWN
wiring so the campaign stays honest: the fixes and detectors we ship here are *product*
changes, not this-repo-specific patches. The `09` bug log is CIP dogfooding its own product.

| Role (product surface) | CIP's own value |
|---|---|
| Language / runtime | Python 3.14.4 (Windows, pwsh 7) |
| Package / CLI | `lib/cipkg/` → `cip` |
| LINT gate instrument (PY) | pyflakes 3.4.0 (`python -m pyflakes lib/cipkg`); ruff drop-in |
| SWALLOW scanner instrument (PY) | `tests/detectors/s1_swallow_scanner.py` (Python `ast`: broad `except` + silent body) → promoted to `cid doctor --static` |
| Dynamic contract probe (PY) | S3 conformance suite (`inspect` + import-graph over `lib/cipkg`) |
| CONFIG validator (PY) | `base.load_config` diff (TOML `config.toml` ↔ code-read keys) + S4 loader suite |
| TEST RUNNER (self-regression) | pytest (`python -m pytest tests/detectors/`) |
| CLI/analyzer surfaces (product) | `cip audit` · `cip analyze` · `cip doctor` · `cip gate` (CI) · `cip sync` |
| Logging/swallow idiom (product) | `lib/cipkg/base.log_swallowed(where, exc)` — fixes MUST surface, never silent |
| Static-analysis surface | language AST/tokenize, extension-dispatched (embedding-free, always) |
| Precision fixture (CLEAN) | `tests/data/clean_ref/` (pinned; **0 FPs mandatory** per detector) |
| Regression locks | `tests/detectors/*_test.py` (fires-on-broken / silent-on-clean) |
| CI gate | `.github/workflows/cip-static-lint-gate.yml` (windows-latest, pwsh, pyflakes+pytest) |
| Dogfood evidence (intact) | `docs/dev/cip-bugfix-campaign/09-bugs-and-issues.md` (869 lines, never edit) |
| Issue inventory | 53 findings: BUG-001..025, ISSUE-101..110, CORE-*, F-01..F-42, manual M1..M4 |

## Per-language detection CIP ships (the portability is IN the product)

CIP's detectors dispatch by file extension so one `cip audit` on a mixed repo speaks one
vocabulary across languages. The S1–S5 prototyped-here family mechanisms are the first
batch; new languages extend the same families, never new one-off scripts.

| Mechanism | Python | JS/TS | Go | Rust | Java/Kotlin | C# |
|---|---|---|---|---|---|---|
| LINT gate | pyflakes/ruff | eslint + @typescript-eslint | go vet / staticcheck | cargo clippy | checkstyle / ktlint | dotnet analyzers |
| Silent-error swallow | AST broad-except scan | no-empty-catch (`catch {}`) | swallowed `_ = err` | `let _ =` / bare unwrap | empty catch block | empty catch block |
| Signature/arity probe | inspect + import-graph | tsc --noEmit / runtime | go build + reflect | cargo test | compiler checks | compiler checks |
| Config drift diff | TOML loader ↔ keys | env/.env/JSON schema | flags/env | toml/env | properties | appsettings |
| Test runner (lock) | pytest | vitest/jest | go test | cargo test | xUnit/TestNG | xUnit |

## Why every fix here is general

Fixing `base.load_config` (F-11), surfacing failed sub-indexers in `stack/audit.py`
(F-24/F-41), routing `suggestion_engine` errors to the log (CORE-52), and shipping the
swallow-scanner as a `doctor --static` step all change **CIP's behavior for every repo it
ever processes** — the 09 rows are only the first consumers of those corrections.