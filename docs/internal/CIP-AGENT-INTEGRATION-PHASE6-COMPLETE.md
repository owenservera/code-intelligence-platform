# Phase 6: Learning Loop - Complete

## Implementation Summary

Successfully implemented the learning loop that feeds agent-caused audit deltas back into the prediction model, completing all 6 phases of the CIP × Coding Agents integration plan.

## What Was Implemented

### `lib/cipkg/learning.py` - Learning Loop System
- **analyze_sessions()**: Analyzes recent sessions to identify patterns and learning signals
  - Tracks agent patterns (verification pass/fail rates, blocked_by patterns)
  - Detects audit drift (findings introduced after agent edits)
  - Identifies risky files with high failure rates
- **update_prediction_confidence()**: Updates prediction model confidence based on learning data
  - Adjusts confidence scores for operations that frequently fail verification
  - Increases confidence for successful patterns
  - Saves adjustments to `confidence_adjustments.json`
- **detect_agent_patterns()**: Placeholder for agent-specific pattern detection
  - Framework for detecting Claude Code vs opencode vs other agent patterns
  - Currently requires agent_type tracking in sessions
- **apply_learning_to_predictions()**: Applies learned confidence adjustments to current predictions
  - Modifies prediction confidence scores based on historical success rates
  - Clamps confidence to valid range [0.0, 1.0]
- **generate_learning_report()**: Comprehensive learning report with actionable insights
  - Summarizes sessions analyzed, verification rate
  - Lists risky files, audit drift, blocked patterns
  - Generates recommendations based on findings

### Integration with `predict.py`
- **Updated predict_next_context()**: Now applies learning-based confidence adjustments
  - Calls `learning.apply_learning_to_predictions()` after generating predictions
  - Returns adjusted predictions with historical confidence data

### Integration with `session.py`
- **Updated session_end()**: Triggers learning loop analysis on session completion
  - Calls `learning.update_prediction_confidence()` after archiving session
  - Non-blocking - doesn't fail session end if learning loop has issues

### CLI Commands Added
- `cip learning analyze` - Analyze recent sessions for patterns
- `cip learning update` - Update prediction confidence based on learning data
- `cip learning report` - Generate comprehensive learning report
- `cip learning patterns` - Detect agent-specific patterns

## How It Works

1. **Session Execution**: Agent runs session with `cip session start`
2. **Session Archive**: `cip session end` archives session with learning data
3. **Learning Analysis**: Learning loop automatically analyzes sessions and updates confidence
4. **Prediction Adjustment**: Future predictions use adjusted confidence scores
5. **Continuous Improvement**: More sessions → better confidence → smarter routing

## Learning Signals Tracked

- **Verification Rate**: Percentage of sessions that pass verification
- **Blocked Patterns**: What causes verification failures (broken_tests, critical_findings, typecheck)
- **Audit Drift**: Critical/high findings introduced by agent edits
- **File Failure Rates**: Files with >50% failure rate across multiple edits
- **Agent Patterns**: Placeholder for agent-type-specific behavior patterns

## Confidence Adjustments

- **Test Operations**: Reduced confidence if broken_tests frequently block verification
- **Audit Operations**: Reduced confidence if critical_findings frequently block verification
- **Schema Operations**: Reduced confidence if typecheck frequently blocks verification
- **Baseline Confidence**: Increased if overall verification rate > 80%

## Usage Examples

```bash
# Analyze recent sessions
cip learning analyze

# Update prediction confidence manually
cip learning update

# Generate learning report
cip learning report

# Detect agent patterns
cip learning patterns
```

## Session Data Structure

Each session archives include:
```json
{
  "session_id": 1234567890,
  "start_time": 1234567890.0,
  "end_time": 1234567990.0,
  "duration_seconds": 100.0,
  "learning": {
    "files_edited": ["src/file.ts", "src/other.ts"],
    "audit_delta": {"critical": 2, "high": 5},
    "test_delta": {"failing_tests": 1, "test_errors": 3},
    "verification_passed": false
  },
  "verification": {
    "can_proceed": false,
    "blocked_by": ["broken_tests", "critical_findings"]
  }
}
```

## Confidence Adjustments File

Stored at `.cip/data/learning/confidence_adjustments.json`:
```json
{
  "updated_at": 1234567890.0,
  "verification_rate": 75.0,
  "adjustments": {
    "test_operations": -0.1,
    "audit_operations": -0.15,
    "schema_operations": -0.1,
    "baseline_confidence": 0.05
  }
}
```

## Future Enhancements

1. **Agent Type Tracking**: Add agent_type field to session metadata for granular analysis
2. **Real-time Learning**: Update confidence during session, not just at end
3. **Pattern Mining**: More sophisticated pattern detection (time-of-day, file-type-specific)
4. **Confidence Decay**: Gradually decay old adjustments to adapt to changing patterns
5. **Explainability**: Show agents why confidence was adjusted (transparent learning)

## Success Metrics

- ✅ Learning loop analyzes sessions and identifies patterns
- ✅ Confidence adjustments saved and applied to predictions
- ✅ Session end triggers learning automatically
- ✅ CLI commands for manual learning management
- ✅ Integration with predict.py for real-time confidence adjustment

## All Phases Complete

**Phase 1**: Auto-Invoke Hooks ✅
**Phase 2**: Agent Awareness & Context ✅
**Phase 3**: Verification Gates ✅
**Phase 4**: MCP Tool Exposure ✅
**Phase 5**: Performance & Structure ✅
**Phase 6**: Learning Loop ✅

The CIP × Coding Agents integration is now fully implemented according to the original priority-ranked plan.