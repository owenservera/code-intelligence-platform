# CIP × Coding Agents: Implementation Progress

## Completed Implementations

### Phase 1: Auto-Invoke Hooks ✅
**Status**: COMPLETE

**Files Created:**
- `lib/cipkg/hooks.py` - Hook system for post-edit and pre-edit hooks
- `.cip/hooks/claude-code.json` - Claude Code hook configuration template
- `.cip/hooks/opencode.json` - opencode hook configuration template

**Files Modified:**
- `lib/cipkg/cli.py` - Hook installation in `cmd_init()`, hook CLI command
- `lib/cipkg/stack/audit.py` - Added `audit_file()` and `audit_diff()` for scoped audits
- `lib/cipkg/stack/impact.py` - Added `impact_structured()` for todo integration

**Features:**
- `cip hook post-edit <file>` - Runs impact + audit after file edits
- `cip hook pre-edit <file> <diff>` - Validates changes against rules before write
- Agent hook configs auto-installed during `cip init`
- Non-blocking warnings for rule violations
- File-scoped and diff-scoped audit for fast incremental checks

### Phase 2: Agent Awareness & Context ✅
**Status**: COMPLETE

**Files Created:**
- `lib/cipkg/session.py` - Session management system
- `lib/cipkg/templates/AGENTS.md` - Agent usage guidelines

**Files Modified:**
- `lib/cipkg/cli.py` - AGENTS.md installation, session CLI commands
- `lib/cipkg/cli.py` - Session command handlers

**Features:**
- `cip session start` - Provides architecture map, broken tests, hotspots, critical findings
- `cip session end` - Collects learning data for feedback loop
- `cip session status` - Shows active session state
- AGENTS.md appended during install with CIP usage guidelines
- Budget-capped context packets to avoid token waste

## Remaining Phases

### Phase 3: Verification Gates (Items 5, 5b)
**Status**: PENDING
- Implement `verify()` function with `cip broken` + optional typecheck/lint
- Integrate verification into session end hook
- Add structured impact output for todo integration
- Create todo integration templates

### Phase 4: MCP Tool Exposure (Item 6)
**Status**: PENDING
- Expose `route_for_agent()` as first-class MCP tool
- Add to TOOLS list in `server.py`
- Update `call_tool()` to handle route calls with context

### Phase 5: Performance & Structure (Items 7, 8, 9)
**Status**: COMPLETE
- ✅ `--diff` flag for scoped audit (implemented in Phase 1)
- ✅ Structured findings output (implemented in Phase 1)
- ✅ Structured impact output (implemented in Phase 1)
- ✅ Token cost tracking in `context()` results (just added)
- ✅ Findings machine-actionable format (implemented in Phase 1)

### Phase 6: Learning Loop (Item 10)
**Status**: PENDING
- Session-end learning loop foundation in Phase 2
- Need to implement `learning.py` for prediction model updates
- Agent-specific pattern detection
- Audit delta feedback integration

## Usage Examples

### Hook Integration
```bash
# Post-edit hook (auto-invoked by agent)
cip hook post-edit src/storage/message.ts

# Pre-edit hook (auto-invoked by agent)  
cip hook pre-edit src/storage/message.ts "diff content"
```

### Session Management
```bash
# Start session with repo context
cip session start

# Check session status
cip session status

# End session with learning loop
cip session end
```

### Scoped Audit
```bash
# File-scoped audit (fast)
cip audit --file src/storage/message.ts

# Diff-scoped audit (incremental)
cip audit --diff
```

### Structured Output
```bash
# Machine-actionable findings
cip findings --structured --severity critical

# Structured impact for todo integration
cip impact --structured target src/storage/message.ts
```

## Next Steps

1. **Phase 3**: Implement verification gates and todo integration
2. **Phase 4**: Expose `route_for_agent()` as MCP tool
3. **Phase 5**: Add token cost tracking to context results
4. **Phase 6**: Implement learning loop with prediction model updates

## Success Metrics

- ✅ Phase 1: Hooks installed and functional
- ✅ Phase 2: Session context and AGENTS.md guidelines  
- ⏳ Phase 3: Verification gates blocking incomplete tasks
- ⏳ Phase 4: `route` tool available via MCP
- ⏳ Phase 5: Token costs exposed, findings fully machine-actionable
- ⏳ Phase 6: Learning loop improving prediction accuracy