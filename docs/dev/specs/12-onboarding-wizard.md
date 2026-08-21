# SPEC-12 — Repo Activation Wizard (FR-12)

- **Requirement source:** `05-requirements.md` §2 FR-12, §7.1(1)(3), §7.2, ISSUE-112
- **Grounding verified:** 2026-08-15 against `lib/cipkg/{init_detector,base,gatekeeper}.py`
- **Build order dependency:** SPEC-10 (config write-back), SPEC-04 (sync job), SPEC-01 (shell CTA).

---

## 1. Goal & owner intent

Activation = **wizard when `.cip` missing, direct attach when present** (§7.1-1; round-2 "Both").
Wizard must be **intelligent AND manually configurable** (§7.1-3): it auto-detects repo type,
suggests include/exclude + embed settings, then lets the owner adjust before running. Full
"magic in what should the console optimize" (§7.1-3) — the wizard's goal is to get a useful,
indexed, live repo with the least friction, while exposing every lever.

## 2. Truth-grounded core surface (verified 2026-08-15)

| Need | Core call (verified) | Returns |
|---|---|---|
| Init state | `init_detector.InitDetector(root).detect()` `init_detector.py:61` | `InitState(status, cip_dir_exists, config_exists, index_exists, index_fresh, git_hooks_installed, agents_md_exists, detection, recommendations)` |
| Status enum | `InitStatus` `init_detector.py:14` | NOT_INITIALIZED / INITIALIZED_NO_INDEX / INITIALIZED_STALE_INDEX / FULLY_INITIALIZED / ERROR |
| Repo detect | `_detect_repo()` `init_detector.py:159` | `RepoDetection(repo_type, languages[], frameworks[], has_git, git_branch, git_uncommitted, file_count)` |
| Freshness | `_check_index_freshness()` `init_detector.py:142` | index.db mtime < 1h |
| UI guidance | `get_init_ui_text / should_launch_dashboard / should_show_index_ui` `init_detector.py:376-405` | text + flags |
| Repo profile | `repo-settings/detectors.detect_repo_type/load_repo_profile` (via `load_config`, `base.py:122-124`) | profile include/exclude/index settings |
| Iteration | `gatekeeper.iter_files_smart(root, cfg)` `gatekeeper.py:168` | tiered file list (index/track/scan/skip) |
| Admission | `gatekeeper.admission_report` `gatekeeper.py:177` / `explain` `gatekeeper.py:196` | tier counts + per-file reason |
| Write config | `.cip/config.toml` via `load_config`+SPEC-10 writer | the wizard's write target |
| Init bundle | `.cip/` (CIP_DIRNAME), `data/`, `config.toml`, hooks, AGENTS.md | created by install (`cip init`) |

## 3. UI/UX contract

- **Wizard flow (NOT_INITIALIZED path):**
  1. **Welcome / choose repo** — auto-detect current dir (`InitDetector.detect`); if not a
     CIP repo, fields: repo path (or "use CWD"), name. Show `_detect_repo` result (languages,
     frameworks, git status, file_count).
  2. **Intelligence preview** — auto-suggested config from `detect_repo_type` + profile:
     language list, include/exclude, `[embed] backend/model`, summary backend, git depth.
     Present each as editable field (SPEC-10 schema widgets) with "why this was chosen" hints.
  3. **Review** — diff of what will be written (`.cip/config.toml` + AGENTS.md if absent +
     hooks enable toggle); "Install CIP bundle" action.
  4. **Index & verify (W5, §7.2)** — run sync as SPEC-04 job with progress; then admission
     report; then seed view (search, health, graph seed) — landing on command center.
- **Direct attach path (INITIALIZED_*):** single "Attach repo" button → validates config +
  freshness → immediately lands on command center (SPEC-01); stale index → offer sync first.
- **Every step cancellable/backable**; config pre-filled but fully editable (manual override).
- **States:** INITIALIZED_NO_INDEX → wizard resumes at step 4; STALE_INDEX → "Sync now"
  CTA; ERROR → error card with `error_message` + permissions tip.
- **Deterministic ordering:** wizard hides nothing but never overwhelms — advanced toggles
  under "Advanced".

## 4. API / WS contract

REST:
- `GET /api/onboarding/status` → `InitDetector.detect()` serialized.
- `POST /api/onboarding/detect` `{path?}` → `RepoDetection` + suggested config (from profile).
- `POST /api/onboarding/install` `{config: {...}, write_agents: bool, enable_hooks: bool}`
  → creates `.cip/` + writes config (SPEC-10 writer) → `{ok, files_written}`.
- `POST /api/onboarding/sync` → `{job_id}` (SPEC-04 sync job; W5 verify follows).
- `GET /api/onboarding/review` → admission report for post-sync transparency.

WS (`/ws`, SPEC-14): `job.progress` (sync), `job.done` (stats), `onboarding.complete` → UI
transitions to command center.

## 5. Data contract

- Writes: `.cip/config.toml` (+`.bak`), `.cip/data/` dir, optionally AGENTS.md (only if absent),
  git hook markers. No DB rows here (sync creates index.db).
- Reads: `InitDetector` filesystem checks, `load_config` profile merge, `iter_files_smart`.

## 6. Backend additions (lib/cipkg in scope)

1. **`web_bridge.onboarding_detect(root)`** — `InitDetector.detect()` + `RepoDetection` + profile-
   based suggested config (composition; both exist but are separate modules).
2. **`web_bridge.onboarding_install(cfg, opts)`** — writes `.cip/config.toml` via SPEC-10
   writer, creates `data/`, optionally writes AGENTS.md (never overwrites existing), returns
   written-file list. (Core `cip init` exists for CLI; bridge mirrors it for the web — verify
   `__init__.py` install path to reuse instead of duplicating.)
3. **Suggested-config generator** — from `detect_repo_type` + `load_repo_profile` + repo
   language evidence; returns editable defaults (embed backend per env, exclude from
   `DEFAULT_EXCLUDES` + per-type, summary backend structural).
4. **W5 post-sync seed** — after sync job, build seed payload (stats + sample search +
   health + graph seed symbol) for the landing handoff (§7.2).

## 7. Core issues / risks (flagged, grounded)

- **CORE-47 — `InitDetector` freshness is hardcoded 1h (index mtime)** `init_detector.py:142-155` —
  differs from `server.index_status` freshness (<300s, `server.py`). Two freshness definitions
  → wizard may say "stale" while status says "fresh". → Bridge uses the SAME freshness source as
  SPEC-01 status; treat `init_detector.index_fresh` as advisory only. *(New issue.)*
- **CORE-48 — `InitDetector` checks `AGENTS.md` existence but wizard must never overwrite an
  existing AGENTS.md.** `init_detector.py:59` reads it; onboarding install must skip if present
  (write only when absent). *(New issue; safe-guard.)*
- **CORE-49 — `_detect_repo` may misclassify (file_count-based heuristics).** `init_detector.py:159-...`
  heuristic detection; wizard's suggested config must be editable because detection can be wrong
  (§7.1-3 manual config). *(Grounds the "manual override" requirement.)*
- **CORE-50 — install path duplication risk: `cip init` (CLI) vs `onboarding_install` (bridge).**
  Two writers → config drift. → Reuse the core install function if importable (verify
  `__init__.py`/`cli.py init`); otherwise bridge mirrors with same defaults. *(New issue.)*
- **Watch: repo_profile auto-detect (`base.py:122-124`) can fail silently (CORE-41)** — wizard
  must show profile source + errors so "magic" doesn't hide a broken profile.
- **Watch: hooks install writes into `.git/hooks/`** — keep behind a toggle; some repos (CI)
  don't want hooks. Default on for local repos, off for mono/CI paths.

## 8. Acceptance checks (from §6 / §7.5)

- [ ] NOT_INITIALIZED → full wizard: detect → suggest → edit → install → sync → seed landing.
- [ ] INITIALIZED_* → direct attach (or sync CTA for stale), no wizard.
- [ ] Every suggested value editable; diff shown before write; AGENTS.md never overwritten.
- [ ] Install writes `.cip/config.toml` (+bak) + data/; hooks behind toggle.
- [ ] Freshness consistent with SPEC-01 status source (CORE-47 resolved).
- [ ] Post-sync W5 seed: stats + sample search + health + graph seed on command center.
