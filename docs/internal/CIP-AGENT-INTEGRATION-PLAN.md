# CIP × Coding Agents Integration Plan

## Analysis Summary

**Current CIP State:**
- ✅ MCP server with 20+ tools already implemented
- ✅ `route_for_agent()` exists but not exposed as MCP tool
- ✅ `predict.py` exists but not integrated into main flow
- ✅ CLI installation can append to AGENTS.md
- ❌ No agent-specific hooks (PostToolUse, PreToolUse, SessionStart, SessionEnd)
- ❌ Findings output is prose, not machine-actionable
- ❌ No session management or standing context
- ❌ No diff-scoped audit
- ❌ No token budget awareness in tool results

## Phased Implementation Plan

### Phase 1: Auto-Invoke Hooks (Items 1, 3) ⭐ Highest Impact
**Goal**: Make CIP fire automatically on file edits, not just on request.

**Implementation:**
1. Create `lib/cipkg/hooks.py` - Hook system for agent integration
2. Add `post_edit_hook(file_path)` - Runs `cip impact` + `cip audit --file` 
3. Add `pre_edit_hook(file_path, diff)` - Validates against rules before write
4. Integrate hooks into CLI `cmd_init()` to install agent hook configs
5. Create hook configuration files for Claude Code and opencode

**Files to Create:**
- `lib/cipkg/hooks.py` - Hook system
- `.cip/hooks/claude-code.json` - Claude Code hook config
- `.cip/hooks/opencode.json` - opencode hook config

**Files to Modify:**
- `lib/cipkg/cli.py` - Hook installation in `cmd_init()`
- `lib/cipkg/stack/audit.py` - Add `--file` scoped audit
- `lib/cipkg/stack/impact.py` - Ensure file-scoped impact works

### Phase 2: Agent Awareness & Context (Items 2, 4) ⭐ High Impact
**Goal**: Displace grep reflexes and provide standing session context.

**Implementation:**
1. Extend `cmd_init()` to append CIP usage guidelines to AGENTS.md
2. Create `lib/cipkg/session.py` - Session management
3. Add `session_start()` - Returns architecture map, broken tests, co-changed files, top findings
4. Add `session_end()` - Logs session summary for learning loop
5. Update `server.py` to expose `session_start` and `session_end` as MCP tools

**Files to Create:**
- `lib/cipkg/session.py` - Session management
- `lib/cipkg/templates/AGENTS.md snippet` - Agent instructions

**Files to Modify:**
- `lib/cipkg/cli.py` - Append to AGENTS.md during install
- `lib/cipkg/server.py` - Add session MCP tools

### Phase 3: Verification Gates (Items 5, 5b) ⭐ High Impact  
**Goal**: Make verification mandatory and structure impact results into todos.

**Implementation:**
1. Add `verify()` function that runs `cip broken` + optional typecheck/lint
2. Integrate verification into session end hook
3. Add structured impact output that can be converted to todo items
4. Create todo integration templates for Claude Code and opencode

**Files to Create:**
- `lib/cipkg/verify.py` - Verification gate
- `.cip/hooks/verification.json` - Verification configuration

**Files to Modify:**
- `lib/cipkg/session.py` - Add verification to session_end
- `lib/cipkg/stack/impact.py` - Add structured output format

### Phase 4: MCP Tool Exposure (Item 6) ⭐ Medium Impact
**Goal**: Expose `route_for_agent()` as first-class MCP tool.

**Implementation:**
1. Add `route_for_agent` to TOOLS list in `server.py`
2. Update `call_tool()` to handle route calls with context
3. Ensure confidence scores and categories are returned

**Files to Modify:**
- `lib/cipkg/server.py` - Add route tool to TOOLS and call_tool

### Phase 5: Performance & Structure (Items 7, 8, 9) ⭐ Medium Impact
**Goal**: Make audit fast/scoped, findings machine-actionable, expose token costs.

**Implementation:**
1. Add `--diff` flag to `cip audit` for git diff-scoped checks
2. Convert findings output to structured `{file, line, rule_id, message, suggested_pattern}`
3. Add token cost tracking to `context()` tool result
4. Optimize diff-scoped audit performance

**Files to Modify:**
- `lib/cipkg/stack/audit.py` - Add `--diff` flag, structured output
- `lib/cipkg/retrieve.py` - Add token cost to context results
- `lib/cipkg/gatekeeper.py` - Structured findings serialization

### Phase 6: Learning Loop (Item 10) ⭐ Long-term Value
**Goal**: Feed agent-caused audit deltas back into prediction model.

**Implementation:**
1. Add audit diff logging to `session_end()`
2. Create `lib/cipkg/learning.py` - Learning loop integration
3. Feed session data into `predict.py` model updates
4. Add agent-specific pattern detection

**Files to Create:**
- `lib/cipkg/learning.py` - Learning loop system
- `.cip/data/learning/` - Session history and patterns

**Files to Modify:**
- `lib/cipkg/session.py` - Add audit diff collection
- `lib/cipkg/predict.py` - Integrate learning feedback

## Implementation Order Rationale

**Phase 1 (Hooks)**: Changes agent behavior without being asked - highest ROI
**Phase 2 (Context)**: Reduces friction once behavior is correct  
**Phase 3 (Verification)**: Closes the most common agentic failure mode
**Phase 4 (MCP Route)**: Reduces tool-selection friction
**Phase 5 (Performance)**: Makes 1-3 fast enough to be sustainable
**Phase 6 (Learning)**: Compounds value once 1-5 are running

## Success Metrics

- **Phase 1**: Hooks installed and firing on file edits
- **Phase 2**: AGENTS.md updated, session context provided
- **Phase 3**: Verification gates blocking incomplete tasks
- **Phase 4**: `route` tool available and used by agents
- **Phase 5**: Diff-scoped audit < 2s, structured findings parsed
- **Phase 6**: Learning loop improving prediction accuracy over time

## Compatibility Notes

- All changes are backward compatible
- Hooks are opt-in via configuration
- Structured outputs maintain prose fallbacks
- Session features work without agent integration