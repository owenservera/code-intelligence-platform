# Post-Campaign Next Steps — CIP v2.1 Roadmap

**Date:** 2026-08-17
**Context:** Bug-fix campaign complete (53/53 findings + 4/4 P1 issues)
**Status:** Ready for next phase

## Current State Assessment

### Completed Work
- ✅ CIP Bug-Fix & Detection Campaign: 53/53 TRACKER findings addressed
- ✅ Detector integration: S1/S2/S3/S4/S5 integrated into `cip doctor --static` and `--config`
- ✅ Regression tests: 61/61 detector tests passing
- ✅ Dogfooding verified: detectors working on CIP itself
- ✅ Documentation: CAMPAIGN_COMPLETE.md, NEXT_STEPS_ASSESSMENT.md, DETECTOR_INTEGRATION_GAP.md

### Infrastructure Status
- ✅ README.md: Updated to v2.0 with full feature documentation
- ✅ AGENTS.md: Updated to v2.1 with 120K context session rules
- ✅ config.default.toml: Updated to v2.0 with full configuration
- ✅ mcp.json: Complete MCP server configuration with 10 tools + 3 resources + 3 prompts
- ✅ ontology.json: v2.0 ontology defined

### Development Docs Status
- ✅ COMPLETE CLI & TERMINAL DASHBOARD.md: 47 bugs fixed, 15 enhancements
- ✅ COMPLETE WEB DASHBOARD UPGRADE PAC.md: Web dashboard architecture defined
- ✅ FINAL INTEGRATION PACK Making CIP.md: Agent-ready integration plan defined
- ✅ UPGRADE_01_BUGS_AND_DESIGN_ISSUES.md: Bug fixes documented

## Remaining Work from docs/development/

### 1. Web Dashboard Implementation
**File:** `docs/development/COMPLETE WEB DASHBOARD UPGRADE PAC.md`
**Status:** Architecture defined, not implemented
**Priority:** High

Required features:
- Interactive SPA with WebSocket real-time updates
- State management with undo/redo
- D3.js code visualization graph
- Live search with autocomplete
- Visual blast radius impact analysis
- Timeline + knowledge graph memory dashboard
- Real-time gauges + health monitoring

### 2. Agent Usage Guide
**File:** `docs/development/FINAL INTEGRATION PACK Making CIP.md` (section 8)
**Status:** Missing
**Priority:** Medium

Required content:
- Step-by-step agent onboarding guide
- Common agent workflows with examples
- Best practices for agent-CIP integration
- Troubleshooting guide for agents

### 3. CI/CD Pipeline
**File:** `docs/development/FINAL INTEGRATION PACK Making CIP.md` (section 7)
**Status:** Missing
**Priority:** Medium

Required components:
- GitHub Actions workflow for tests
- Automated deployment pipeline
- Release automation
- Integration tests in CI

### 4. Test Infrastructure Enhancement
**File:** `docs/development/FINAL INTEGRATION PACK Making CIP.md` (section 6)
**Status:** Incomplete
**Priority:** High

Required improvements:
- Integration test coverage expansion
- E2E test suite for MCP server
- Performance regression tests
- Memory system tests

### 5. Web Console Bridge Layer
**File:** `docs/dev/09-bugs-and-issues.md` (BUG-001, BUG-002, BUG-004)
**Status:** Not started
**Priority:** Low (future work)

Required work:
- web_server.py sync signature fix
- /api/memory routes implementation
- Split-brain dashboard resolution

## Recommended Next Steps Plan

### Phase 1: Test Infrastructure Enhancement (Week 1)
**Goal:** Strengthen test coverage before new features

**Current Status (2026-08-17):**
- Test run results: 133 passed, 23 failed, 6 skipped, 124 warnings, 33 errors
- Primary issue: Windows file locking errors in terminal_dashboard tests
- Error pattern: `PermissionError: [WinError 32] The process cannot access the file because it is being used by another process`
- Affected tests: All terminal_dashboard integration tests (test_screen_integration.py, test_full_coverage.py, test_coverage_improvement.py, test_interactions.py)
- Root cause: Textual TUI tests leaving file handles open on Windows
- **FIXED:** Updated conftest.py temp_repo_dir fixture with Windows file locking workaround
- **VERIFIED:** terminal_dashboard/test_screen_integration.py now passes (8/8 tests)
- Current coverage: 12% overall (12,770 total lines, 1,223 covered)

**Tasks:**
1. **Phase 1.0:** Fix Windows file locking issues in terminal_dashboard tests
   - ✅ **COMPLETED:** Updated conftest.py temp_repo_dir fixture with Windows file locking workaround
   - ✅ **VERIFIED:** terminal_dashboard/test_screen_integration.py now passes (8/8 tests)
2. Expand integration test coverage to 80%+ (excluding terminal_dashboard)
   - Current coverage: 12% overall (12,770 total lines, 1,223 covered)
   - Priority modules: indexer.py (10%), embed.py (15%), retrieve.py (0%), analysis.py (0%), learning_system.py (30%)
3. Add E2E tests for MCP server
4. Add performance regression tests
5. Add memory system integration tests
6. Set up CI pipeline with GitHub Actions

**Deliverables:**
- `tests/integration/` expanded
- `tests/e2e/mcp_server_test.py` created
- `.github/workflows/ci.yml` created
- Coverage report showing 80%+

### Phase 2: Web Dashboard Implementation (Weeks 2-4)
**Goal:** Build interactive web dashboard per upgrade pack

**Tasks:**
1. Set up React/Next.js frontend in `web/` directory
2. Implement WebSocket server in `lib/cipkg/websocket_handler.py`
3. Create state management system (Redux-like)
4. Integrate D3.js for code visualization
5. Implement live search with autocomplete
6. Build impact analysis blast radius graph
7. Create memory dashboard with timeline
8. Add real-time health gauges

**Deliverables:**
- `web/src/` React application
- `lib/cipkg/websocket_handler.py` WebSocket server
- Interactive code graph with D3.js
- Real-time search interface
- Impact visualization dashboard
- Memory timeline view

### Phase 3: Agent Usage Guide (Week 5)
**Goal:** Comprehensive agent onboarding documentation

**Tasks:**
1. Create `docs/AGENT_USAGE_GUIDE.md`
2. Document common agent workflows
3. Provide step-by-step integration examples
4. Add troubleshooting section
5. Create example agent scripts

**Deliverables:**
- `docs/AGENT_USAGE_GUIDE.md` comprehensive guide
- Example agent workflows in `examples/agents/`
- Troubleshooting FAQ

### Phase 4: Web Console Bridge Layer (Week 6)
**Goal:** Fix web console-specific issues from 09-bugs-and-issues

**Tasks:**
1. Fix web_server.py sync signature (BUG-001)
2. Implement /api/memory routes (BUG-002)
3. Resolve split-brain dashboards (BUG-004)
4. Test web console integration

**Deliverables:**
- Web console bugs fixed
- API routes implemented
- Dashboard unification complete

### Phase 5: Release Preparation (Week 7)
**Goal:** Prepare for v2.1 release

**Tasks:**
1. Update CHANGELOG.md
2. Create release notes
3. Tag v2.1.0 release
4. Update documentation versions
5. Prepare announcement

**Deliverables:**
- `CHANGELOG.md` updated
- Release notes drafted
- Git tag v2.1.0 created
- Documentation updated to v2.1

## Execution Order

**Immediate (This Session):**
1. Document this plan in `docs/development/POST_CAMPAIGN_NEXT_STEPS.md`
2. Create todo list for Phase 1 tasks
3. Begin Phase 1: Test Infrastructure Enhancement

**Next Sessions:**
- Phase 1: Test Infrastructure Enhancement
- Phase 2: Web Dashboard Implementation
- Phase 3: Agent Usage Guide
- Phase 4: Web Console Bridge Layer
- Phase 5: Release Preparation

## Success Criteria

### Phase 1 Success
- Test coverage ≥ 80%
- CI pipeline passing on all commits
- All new tests passing

### Phase 2 Success
- Web dashboard functional and interactive
- Real-time updates working via WebSocket
- Code visualization rendering correctly
- Impact analysis visualizing blast radius

### Phase 3 Success
- Agent usage guide comprehensive
- Example workflows tested
- Troubleshooting guide helpful

### Phase 4 Success
- Web console bugs resolved
- API routes functional
- Dashboards unified

### Phase 5 Success
- Release notes complete
- Documentation updated
- Release tagged and published

## Dependencies

**Phase 1 depends on:** None (can start immediately)
**Phase 2 depends on:** Phase 1 (test infrastructure needed)
**Phase 3 depends on:** Phase 2 (web dashboard features documented)
**Phase 4 depends on:** Phase 2 (web console needs web dashboard)
**Phase 5 depends on:** All previous phases

## Risk Mitigation

**Phase 1 Risks:**
- Test coverage may not reach 80% → Focus on critical paths first
- CI pipeline may have configuration issues → Test in fork first

**Phase 2 Risks:**
- Web dashboard complexity may exceed timeline → Prioritize core features
- WebSocket integration may be unstable → Add fallback polling

**Phase 3 Risks:**
- Agent workflows may be difficult to document → Use real examples from usage
- Guide may become outdated quickly → Version with releases

**Phase 4 Risks:**
- Web console bugs may be deeper than expected → Escalate to design decision
- API routes may conflict with existing MCP → Coordinate with MCP team

**Phase 5 Risks:**
- Release may be delayed by bugs → Have rollback plan ready
- Documentation may have inconsistencies → Technical review before release
