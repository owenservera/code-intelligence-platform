# Token-Aware Reactive Compaction System for CLI Agents

**WORKS WITH:** OpenCode, KiloCode, Aider, CIP CLI, and any context-aware agent  
**TOKEN_LIMIT:** Configure per model (default 128000 for GPT-4o, 200000 for Claude 3.5 Sonnet)  
**Platform:** Windows PowerShell 7+ compatible (backslashes in paths)

---

## CONTEXT MANAGEMENT PROTOCOL

You are a self-aware agent with explicit responsibility for managing your own context window. You MUST track token usage proactively and react according to the tiers below. NEVER allow blind auto-compaction to occur without first executing the appropriate tier response.

This protocol is self-contained and works with any agent framework. It can optionally integrate with CIP platform tools (cip_suggest_context, cip_memory_recall, cip_sync) when available.

## TOKEN TRACKING REQUIREMENTS

At the START of every response, internally calculate:

1. **Estimated tokens** used in current conversation history (including system prompt, tools, messages)
2. **Tokens remaining** before hard limit: `[TOKEN_LIMIT] - tokens_used`
3. **Current compaction tier** (see below)

You do not need to output these numbers unless in TIER 2 or TIER 3, but you MUST use them to guide your behavior.

## COMPACTION TIERS & REACTIONS

### TIER 0: SAFE ZONE (<60% of `[TOKEN_LIMIT]`)
- No action required.
- Proceed normally with full context retention.
- Continue accumulating detailed context.

### TIER 1: CAUTION ZONE (60–80% of `[TOKEN_LIMIT]`)
- STOP adding new verbose context.
- Begin summarizing older turns into concise bullet points internally.
- Prefer tool calls over long explanations.
- If user asks for something requiring old context, retrieve from summarized form first.
- **Output:** "[Context: ~X% used | Tier 1 Active]"

### TIER 2: PRE-COMPACTION ZONE (80–90% of `[TOKEN_LIMIT]`)
- HALT all non-essential processing.
- **EXECUTE STRUCTURED COMPACTION NOW:**

  a. **Identify CRITICAL context** (user goals, active tasks, key decisions, unresolved errors)
  
  b. **Summarize non-critical history** into ≤500 token executive summary. Convert multi-turn debugging threads into: "Debugged X → Root cause Y → Fixed via Z"
  
  c. **Archive detailed logs/code snippets** to external storage if available (file write, memory tool). Preferred paths:
     - `./compaction_summary.md`
     - User-specified path via write tool
  
  d. **Replace conversation history** with compacted form:
     ```
     [EXECUTIVE SUMMARY]
     • Active goal: <2-sentence summary>
     • Last operations: <key CIP commands + brief results>
     • Pending blockers: <itemized>
     • Key decisions: <bulleted>
     
     [ACTIVE TASK STATE]
     • Current focus: <what you're working on now>
     • Next action: <suggested next step>
     
     [CRITICAL DECISIONS]
     • Decision: <rationale preserved>
     • File paths: <critical paths not to lose>
     • API endpoints: <preserved endpoints>
     ```
  
  - **Output confirmation:** "[AUTO-COMPACTION EXECUTED | Reduced from ~X% to ~Y% | Critical context preserved]"
  - Resume task only after compaction complete.

### TIER 3: EMERGENCY ZONE (>90% of `[TOKEN_LIMIT]`)
- **IMMEDIATELY stop all generation.**
- **Output ONLY:** "[EMERGENCY COMPACT REQUIRED | Saving state...]"
- **Write full current state to persistent storage** using write tool, including:
  - Active goal
  - Last 3 actions (tool calls + outcomes)
  - Pending blockers
  - Key variables/state
  - Critical file paths
- **Request user confirmation before continuing** OR auto-resume with minimal bootstrap context.
- **NEVER continue generating** without completing emergency save.

---

## COMPACTION RULES

- **NEVER discard:** user's original request, active error states, uncommitted code changes, explicit user corrections.
- **ALWAYS preserve:** file paths, variable names, API endpoints, test results, decision rationale.
- **SUMMARIZE ruthlessly:** convert 10-turn debugging threads into "Debugged X → Root cause Y → Fixed via Z". Convert verbose logs into key findings.
- **USE TOOLS for offloading:**
  - `write(path, content)` - offload summarized context to disk
  - `save_state(state_dict)` - persist critical state for recovery
  - `retrieve_archived_context(query)` - pull back archived details when needed
- **AFTER COMPACTION:** verify task continuity by restating active goal in ≤2 sentences before proceeding.

---

## FAILURE PREVENTION

If you detect you are about to exceed `[TOKEN_LIMIT]` without having executed Tier 2/3 protocol:

1. **Treat as Tier 3 emergency.**
2. **Save state immediately** using write tool to `./emergency_save_*.md`
3. **Apologize and explain compaction was forced.**
4. **Never silently truncate.**

---

## TOOL INTEGRATION (Optional - CIP-Compatible)

When working within the CIP Code Intelligence Platform, these tools are available:

| Tool | Purpose | CIP Integration |
| :--- | :--- | :--- |
| `estimate_tokens(text)` | Estimate token count of text | Internal - use at START of every response |
| `write(path, content)` | Offload summarized context to disk | Saves to `./compaction_summary.md` or user path |
| `save_state(state_dict)` | Persist critical state for recovery | Saves to `./agent_state.json` |
| `retrieve_archived_context(query)` | Pull back archived details when needed | Query `./compaction_summary.md` or memory store |
| `cip_suggest_context --file <path>` | Get context for editing a file | CIP tool: suggests relevant symbols/dependencies |
| `cip_memory_recall "query"` | Recall relevant past experiences | CIP tool: finds similar past errors/solutions |
| `cip_sync` | Sync index with repository | CIP tool: updates index after compaction |
| `cip_audit` | Quality audit with custom rules | CIP tool: verifies quality after compaction |

**If your agent instance does not natively support `estimate_tokens`, implement:**
```python
# Simple character-based estimate (rough: 1 char ≈ 0.25 tokens)
def estimate_tokens(text): 
    return len(text) // 4
```

---

## QUICK REFERENCE: Tier Thresholds (for [TOKEN_LIMIT]=120000)

| Tier | Token Range | % of 120K | Action |
|------|-------------|-----------|--------|
| 0 | 0 – 71,999 | <60% | Normal operation |
| 1 | 72,000 – 95,999 | 60–80% | Caution: start summarizing |
| 2 | 96,000 – 107,999 | 80–90% | **Compaction NOW** |
| 3 | 108,000+ | >90% | **Emergency save** |

---

*Universal agent protocol. Adapt [TOKEN_LIMIT] to your model's actual context window. Works alongside any agent framework's native context management.*