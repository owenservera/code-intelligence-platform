# ≡ƒôè CIP Repository Forensic Intelligence & Master Data Report (L0ΓÇôLA)

**Overall Health Grade:** `F` (19.2/100)  
**Generated:** 2026-08-21 17:44:58  

---

## 1. 5-Dimensional Health Scorecard

| Dimension | Score | Grade | Status |
| :--- | :--- | :--- | :--- |
| **1. Reliability & Flow (L4)** | 15.0% | `F` | ΓÜá∩╕Å Needs Attention |
| **2. Security & Secrets (L7)** | 10.0% | `F` | ΓÜá∩╕Å Needs Attention |
| **3. Architecture & Boundaries (L5)** | 20.0% | `F` | ΓÜá∩╕Å Needs Attention |
| **4. Code Quality & Smells (L6)** | 30.0% | `F` | ΓÜá∩╕Å Needs Attention |
| **5. Evolution & Churn Risk (L9)** | 30.0% | `F` | ΓÜá∩╕Å Needs Attention |

**Active Finding Inventory:** ≡ƒö┤ Critical: `129` ┬╖ ≡ƒƒá High: `141` ┬╖ ≡ƒƒí Medium: `2`

---

## 2. ≡ƒù║∩╕Å Critical Wiring Gaps & Silent Runtime Traps (L4)

### #1 [HIGH] Silent Wiring Gap: DEAD_EVENT_LISTENER 'dragstart.drag'
- **Location:** `lib/cipkg/static/lib/d3.v7.min.js:2`
- **Detail:** Listener registered for 'dragstart.drag' but no emitter was found in the codebase
- **Actionable Suggestion:** Wire up the frontend caller and backend handler with identical naming or remove orphaned registration.

### #2 [HIGH] Silent Wiring Gap: DEAD_EVENT_LISTENER 'focus'
- **Location:** `lib/cipkg/static/js/search.js:37`
- **Detail:** Listener registered for 'focus' but no emitter was found in the codebase
- **Actionable Suggestion:** Wire up the frontend caller and backend handler with identical naming or remove orphaned registration.

### #3 [HIGH] Silent Wiring Gap: DEAD_EVENT_LISTENER 'mousedown.brush'
- **Location:** `lib/cipkg/static/lib/d3.v7.min.js:2`
- **Detail:** Listener registered for 'mousedown.brush' but no emitter was found in the codebase
- **Actionable Suggestion:** Wire up the frontend caller and backend handler with identical naming or remove orphaned registration.

### #4 [HIGH] Silent Wiring Gap: DEAD_EVENT_LISTENER 'mousedown.drag'
- **Location:** `lib/cipkg/static/lib/d3.v7.min.js:2`
- **Detail:** Listener registered for 'mousedown.drag' but no emitter was found in the codebase
- **Actionable Suggestion:** Wire up the frontend caller and backend handler with identical naming or remove orphaned registration.

### #5 [HIGH] Silent Wiring Gap: DEAD_EVENT_LISTENER 'drag'
- **Location:** `lib/cipkg/static/js/impact.js:260`
- **Detail:** Listener registered for 'drag' but no emitter was found in the codebase
- **Actionable Suggestion:** Wire up the frontend caller and backend handler with identical naming or remove orphaned registration.

### #6 [HIGH] Silent Wiring Gap: DEAD_EVENT_LISTENER 'input'
- **Location:** `lib/cipkg/static/js/search.js:35`
- **Detail:** Listener registered for 'input' but no emitter was found in the codebase
- **Actionable Suggestion:** Wire up the frontend caller and backend handler with identical naming or remove orphaned registration.

### #7 [HIGH] Silent Wiring Gap: DEAD_EVENT_LISTENER 'keydown.brush'
- **Location:** `lib/cipkg/static/lib/d3.v7.min.js:2`
- **Detail:** Listener registered for 'keydown.brush' but no emitter was found in the codebase
- **Actionable Suggestion:** Wire up the frontend caller and backend handler with identical naming or remove orphaned registration.

### #8 [HIGH] Silent Wiring Gap: DEAD_EVENT_LISTENER 'keydown.brush keyup.brush mousemove.brush mouseup.brush'
- **Location:** `lib/cipkg/static/lib/d3.v7.min.js:2`
- **Detail:** Listener registered for 'keydown.brush keyup.brush mousemove.brush mouseup.brush' but no emitter was found in the codebase
- **Actionable Suggestion:** Wire up the frontend caller and backend handler with identical naming or remove orphaned registration.

### #9 [HIGH] Silent Wiring Gap: DEAD_EVENT_LISTENER 'touchend.drag touchcancel.drag'
- **Location:** `lib/cipkg/static/lib/d3.v7.min.js:2`
- **Detail:** Listener registered for 'touchend.drag touchcancel.drag' but no emitter was found in the codebase
- **Actionable Suggestion:** Wire up the frontend caller and backend handler with identical naming or remove orphaned registration.

### #10 [HIGH] Silent Wiring Gap: DEAD_EVENT_LISTENER 'DOMContentLoaded'
- **Location:** `lib/cipkg/static/js/components.js:504`
- **Detail:** Listener registered for 'DOMContentLoaded' but no emitter was found in the codebase
- **Actionable Suggestion:** Wire up the frontend caller and backend handler with identical naming or remove orphaned registration.

### #11 [HIGH] Silent Wiring Gap: DEAD_EVENT_LISTENER 'mousemove.zoom'
- **Location:** `lib/cipkg/static/lib/d3.v7.min.js:2`
- **Detail:** Listener registered for 'mousemove.zoom' but no emitter was found in the codebase
- **Actionable Suggestion:** Wire up the frontend caller and backend handler with identical naming or remove orphaned registration.

---

## 3. ≡ƒÄ» Prioritized Finding Records with Explainability Traces (LA)

### #1 [HIGH] High Churn ├ù Complexity Hotspot: 'load_config' (Risk Score: 95.0)
- **Rule / Layer:** `HOTSPOT-RISK` (`L9`)
- **Location:** `lib/cipkg/base.py:118`
- **Detail:** Top-decile mutation frequency (churn=7.0) compounded by structural complexity (163.6).
- **Suggested Remediation:** Refactor into smaller, decoupled helper functions and verify test coverage.

**≡ƒöì Explainability Trace:**
1. **[L0]** File: lib/cipkg/base.py
1. **[L1]** Function 'load_config' definition
1. **[L6]** Cognitive complexity metric: 163.6
1. **[L9]** Git commit churn score: 7.0
1. **[LA]** Synthesized composite risk score: 1145.2

### #2 [HIGH] High Churn ├ù Complexity Hotspot: '_parse_toml_naive' (Risk Score: 95.0)
- **Rule / Layer:** `HOTSPOT-RISK` (`L9`)
- **Location:** `lib/cipkg/base.py:105`
- **Detail:** Top-decile mutation frequency (churn=7.0) compounded by structural complexity (7.1).
- **Suggested Remediation:** Refactor into smaller, decoupled helper functions and verify test coverage.

**≡ƒöì Explainability Trace:**
1. **[L0]** File: lib/cipkg/base.py
1. **[L1]** Function '_parse_toml_naive' definition
1. **[L6]** Cognitive complexity metric: 7.1
1. **[L9]** Git commit churn score: 7.0
1. **[LA]** Synthesized composite risk score: 49.7

### #3 [HIGH] High Churn ├ù Complexity Hotspot: 'data_dir' (Risk Score: 95.0)
- **Rule / Layer:** `HOTSPOT-RISK` (`L9`)
- **Location:** `lib/cipkg/base.py:86`
- **Detail:** Top-decile mutation frequency (churn=7.0) compounded by structural complexity (42.3).
- **Suggested Remediation:** Refactor into smaller, decoupled helper functions and verify test coverage.

**≡ƒöì Explainability Trace:**
1. **[L0]** File: lib/cipkg/base.py
1. **[L1]** Function 'data_dir' definition
1. **[L6]** Cognitive complexity metric: 42.3
1. **[L9]** Git commit churn score: 7.0
1. **[LA]** Synthesized composite risk score: 296.1

### #4 [HIGH] High Churn ├ù Complexity Hotspot: 'cip_dir' (Risk Score: 95.0)
- **Rule / Layer:** `HOTSPOT-RISK` (`L9`)
- **Location:** `lib/cipkg/base.py:84`
- **Detail:** Top-decile mutation frequency (churn=7.0) compounded by structural complexity (30.1).
- **Suggested Remediation:** Refactor into smaller, decoupled helper functions and verify test coverage.

**≡ƒöì Explainability Trace:**
1. **[L0]** File: lib/cipkg/base.py
1. **[L1]** Function 'cip_dir' definition
1. **[L6]** Cognitive complexity metric: 30.1
1. **[L9]** Git commit churn score: 7.0
1. **[LA]** Synthesized composite risk score: 210.7

### #5 [HIGH] High Churn ├ù Complexity Hotspot: 'repo_root' (Risk Score: 95.0)
- **Rule / Layer:** `HOTSPOT-RISK` (`L9`)
- **Location:** `lib/cipkg/base.py:74`
- **Detail:** Top-decile mutation frequency (churn=7.0) compounded by structural complexity (146.8).
- **Suggested Remediation:** Refactor into smaller, decoupled helper functions and verify test coverage.

**≡ƒöì Explainability Trace:**
1. **[L0]** File: lib/cipkg/base.py
1. **[L1]** Function 'repo_root' definition
1. **[L6]** Cognitive complexity metric: 146.8
1. **[L9]** Git commit churn score: 7.0
1. **[LA]** Synthesized composite risk score: 1027.6

### #6 [HIGH] High Churn ├ù Complexity Hotspot: 'log_swallowed' (Risk Score: 95.0)
- **Rule / Layer:** `HOTSPOT-RISK` (`L9`)
- **Location:** `lib/cipkg/base.py:6`
- **Detail:** Top-decile mutation frequency (churn=7.0) compounded by structural complexity (14.4).
- **Suggested Remediation:** Refactor into smaller, decoupled helper functions and verify test coverage.

**≡ƒöì Explainability Trace:**
1. **[L0]** File: lib/cipkg/base.py
1. **[L1]** Function 'log_swallowed' definition
1. **[L6]** Cognitive complexity metric: 14.4
1. **[L9]** Git commit churn score: 7.0
1. **[LA]** Synthesized composite risk score: 100.8

### #7 [HIGH] High Churn ├ù Complexity Hotspot: '_evidence' (Risk Score: 95.0)
- **Rule / Layer:** `HOTSPOT-RISK` (`L9`)
- **Location:** `tests/detectors/s3_conformance_test.py:44`
- **Detail:** Top-decile mutation frequency (churn=3.0) compounded by structural complexity (18.1).
- **Suggested Remediation:** Refactor into smaller, decoupled helper functions and verify test coverage.

**≡ƒöì Explainability Trace:**
1. **[L0]** File: tests/detectors/s3_conformance_test.py
1. **[L1]** Function '_evidence' definition
1. **[L6]** Cognitive complexity metric: 18.1
1. **[L9]** Git commit churn score: 3.0
1. **[LA]** Synthesized composite risk score: 54.3

### #8 [HIGH] High Churn ├ù Complexity Hotspot: '_open_findings' (Risk Score: 91.85)
- **Rule / Layer:** `HOTSPOT-RISK` (`L9`)
- **Location:** `lib/cipkg/analysis.py:35`
- **Detail:** Top-decile mutation frequency (churn=3.0) compounded by structural complexity (9.3).
- **Suggested Remediation:** Refactor into smaller, decoupled helper functions and verify test coverage.

**≡ƒöì Explainability Trace:**
1. **[L0]** File: lib/cipkg/analysis.py
1. **[L1]** Function '_open_findings' definition
1. **[L6]** Cognitive complexity metric: 9.3
1. **[L9]** Git commit churn score: 3.0
1. **[LA]** Synthesized composite risk score: 27.9

### #9 [HIGH] High Churn ├ù Complexity Hotspot: '_calculate_health_score' (Risk Score: 85.1)
- **Rule / Layer:** `HOTSPOT-RISK` (`L9`)
- **Location:** `lib/cipkg/analysis.py:51`
- **Detail:** Top-decile mutation frequency (churn=3.0) compounded by structural complexity (7.8).
- **Suggested Remediation:** Refactor into smaller, decoupled helper functions and verify test coverage.

**≡ƒöì Explainability Trace:**
1. **[L0]** File: lib/cipkg/analysis.py
1. **[L1]** Function '_calculate_health_score' definition
1. **[L6]** Cognitive complexity metric: 7.8
1. **[L9]** Git commit churn score: 3.0
1. **[LA]** Synthesized composite risk score: 23.4

### #10 [HIGH] Silent Wiring Gap: DEAD_EVENT_LISTENER 'dragstart.drag' (Risk Score: 85.0)
- **Rule / Layer:** `WIRING-GAP` (`L4`)
- **Location:** `lib/cipkg/static/lib/d3.v7.min.js:2`
- **Detail:** Listener registered for 'dragstart.drag' but no emitter was found in the codebase
- **Suggested Remediation:** Wire up the frontend caller and backend handler with identical naming or remove orphaned registration.

**≡ƒöì Explainability Trace:**
1. **[L0]** File exists in topology: lib/cipkg/static/lib/d3.v7.min.js
1. **[L1]** Invocation site at line 2
1. **[L4]** Cross-correlation failed: Listener registered for 'dragstart.drag' but no emitter was found in the codebase
1. **[LA]** Synthesized as High-Severity Silent Failure Risk (Wiring Gap)

### #11 [HIGH] Silent Wiring Gap: DEAD_EVENT_LISTENER 'focus' (Risk Score: 85.0)
- **Rule / Layer:** `WIRING-GAP` (`L4`)
- **Location:** `lib/cipkg/static/js/search.js:37`
- **Detail:** Listener registered for 'focus' but no emitter was found in the codebase
- **Suggested Remediation:** Wire up the frontend caller and backend handler with identical naming or remove orphaned registration.

**≡ƒöì Explainability Trace:**
1. **[L0]** File exists in topology: lib/cipkg/static/js/search.js
1. **[L1]** Invocation site at line 37
1. **[L4]** Cross-correlation failed: Listener registered for 'focus' but no emitter was found in the codebase
1. **[LA]** Synthesized as High-Severity Silent Failure Risk (Wiring Gap)

### #12 [HIGH] Silent Wiring Gap: DEAD_EVENT_LISTENER 'mousedown.brush' (Risk Score: 85.0)
- **Rule / Layer:** `WIRING-GAP` (`L4`)
- **Location:** `lib/cipkg/static/lib/d3.v7.min.js:2`
- **Detail:** Listener registered for 'mousedown.brush' but no emitter was found in the codebase
- **Suggested Remediation:** Wire up the frontend caller and backend handler with identical naming or remove orphaned registration.

**≡ƒöì Explainability Trace:**
1. **[L0]** File exists in topology: lib/cipkg/static/lib/d3.v7.min.js
1. **[L1]** Invocation site at line 2
1. **[L4]** Cross-correlation failed: Listener registered for 'mousedown.brush' but no emitter was found in the codebase
1. **[LA]** Synthesized as High-Severity Silent Failure Risk (Wiring Gap)

### #13 [HIGH] Silent Wiring Gap: DEAD_EVENT_LISTENER 'mousedown.drag' (Risk Score: 85.0)
- **Rule / Layer:** `WIRING-GAP` (`L4`)
- **Location:** `lib/cipkg/static/lib/d3.v7.min.js:2`
- **Detail:** Listener registered for 'mousedown.drag' but no emitter was found in the codebase
- **Suggested Remediation:** Wire up the frontend caller and backend handler with identical naming or remove orphaned registration.

**≡ƒöì Explainability Trace:**
1. **[L0]** File exists in topology: lib/cipkg/static/lib/d3.v7.min.js
1. **[L1]** Invocation site at line 2
1. **[L4]** Cross-correlation failed: Listener registered for 'mousedown.drag' but no emitter was found in the codebase
1. **[LA]** Synthesized as High-Severity Silent Failure Risk (Wiring Gap)

### #14 [HIGH] Silent Wiring Gap: DEAD_EVENT_LISTENER 'drag' (Risk Score: 85.0)
- **Rule / Layer:** `WIRING-GAP` (`L4`)
- **Location:** `lib/cipkg/static/js/impact.js:260`
- **Detail:** Listener registered for 'drag' but no emitter was found in the codebase
- **Suggested Remediation:** Wire up the frontend caller and backend handler with identical naming or remove orphaned registration.

**≡ƒöì Explainability Trace:**
1. **[L0]** File exists in topology: lib/cipkg/static/js/impact.js
1. **[L1]** Invocation site at line 260
1. **[L4]** Cross-correlation failed: Listener registered for 'drag' but no emitter was found in the codebase
1. **[LA]** Synthesized as High-Severity Silent Failure Risk (Wiring Gap)

### #15 [HIGH] Silent Wiring Gap: DEAD_EVENT_LISTENER 'input' (Risk Score: 85.0)
- **Rule / Layer:** `WIRING-GAP` (`L4`)
- **Location:** `lib/cipkg/static/js/search.js:35`
- **Detail:** Listener registered for 'input' but no emitter was found in the codebase
- **Suggested Remediation:** Wire up the frontend caller and backend handler with identical naming or remove orphaned registration.

**≡ƒöì Explainability Trace:**
1. **[L0]** File exists in topology: lib/cipkg/static/js/search.js
1. **[L1]** Invocation site at line 35
1. **[L4]** Cross-correlation failed: Listener registered for 'input' but no emitter was found in the codebase
1. **[LA]** Synthesized as High-Severity Silent Failure Risk (Wiring Gap)

