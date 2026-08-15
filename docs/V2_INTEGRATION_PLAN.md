# CIP CLI v2.0 Integration Plan

## Executive Summary

This document provides a comprehensive plan for integrating CIP CLI v2.0 features into the existing CLI architecture. The integration maintains backward compatibility while adding intelligent, context-aware capabilities.

## Current CLI Architecture Analysis

### Entry Points
- **Primary Entry**: `bin/cip` - Universal wrapper that finds repo root and delegates to CLI
- **CLI Logic**: `lib/cipkg/cli.py` - Argparse-based command dispatch with 40+ existing commands
- **Configuration**: `lib/cipkg/base.py` - Config loading via `load_config(root)`
- **Repository Root**: `lib/cipkg/base.py` - `repo_root()` function to find .cip directory

### Existing Command Structure
```python
# Current dispatch pattern
handlers = {
    "init": handle_init_command,
    "sync": handle_sync_command,
    "search": handle_search_command,
    "audit": handle_audit_command,
    # ... 40+ commands
}
```

### Configuration System
- **Location**: `.cip/config.toml` in repository
- **Loading**: `load_config(root)` from `cipkg.base`
- **Structure**: Flat TOML with sections for git, serve, etc.

## v2.0 Components Analysis

### New Modules Created
1. **context_manager.py** (580 lines)
   - Context building with providers (repository, git, filesystem, system)
   - Caching and serialization
   - Multi-scope context (repository, user, session, system)

2. **suggestion_engine.py** (590 lines)
   - Multi-analyzer suggestion generation
   - Ranking and filtering engines
   - Stack-specific analyzers (Next.js, Python, generic)

3. **error_system.py** (860 lines)
   - Error detection and classification
   - Recovery strategies and logging
   - Error prevention and pattern learning

4. **help_system.py** (220 lines)
   - Context-aware help generation
   - Repository-type specific help
   - Suggestion display

5. **workflow_engine.py** (900 lines)
   - Workflow definition and execution
   - State persistence and resume
   - Built-in workflows (pre-commit, diagnosis)

6. **learning_system.py** (650 lines)
   - Pattern collection and analysis
   - User profiles and personalization
   - Command sequence and time-based patterns

7. **command_adapter.py** (450 lines)
   - Context-aware command adaptation
   - Adapters for audit, search, index, sync, routes
   - Automatic flag injection based on context

8. **interactive_ui.py** (600 lines)
   - Terminal UI components (menus, progress bars, tables)
   - Screen designs (welcome, workflow, search, settings)
   - Accessibility features

9. **interactive.py** (300 lines)
   - Interactive mode orchestrator
   - Integration of all v2.0 features
   - Main interactive loop

10. **config.v2.default.toml** (150 lines)
    - Complete v2.0 configuration structure
    - Interactive mode, learning, adaptation settings

## Integration Strategy

### Phase 1: Configuration Integration

**Objective**: Merge v2.0 configuration with existing config system

**Approach**:
1. Extend `load_config()` to merge v2.0 defaults
2. Add v2.0 config sections to existing config.toml
3. Ensure backward compatibility with existing configs

**Changes Required**:
- Modify `lib/cipkg/base.py::load_config()`
- Add v2.0 config validation
- Create config migration utility

**Implementation Steps**:
```python
# In lib/cipkg/base.py
def load_config(root):
    """Load and merge v1.0 and v2.0 configurations."""
    # Load existing v1.0 config
    config = _load_v1_config(root)
    
    # Merge v2.0 defaults
    v2_config = _load_v2_defaults()
    config = _merge_configs(config, v2_config)
    
    # Load user overrides
    user_config = _load_user_config(root)
    config = _merge_configs(config, user_config)
    
    return config
```

### Phase 2: Context Manager Integration

**Objective**: Initialize context manager in CLI entry points

**Approach**:
1. Initialize context manager in `main()` function
2. Build context once per CLI invocation
3. Pass context to command handlers

**Changes Required**:
- Modify `lib/cipkg/cli.py::main()`
- Add context initialization
- Update command handler signatures to accept context

**Implementation Steps**:
```python
# In lib/cipkg/cli.py
def main(argv=None):
    p = setup_argument_parser()
    a = p.parse_args(argv)
    if not a.cmd:
        p.print_help()
        return 0
    
    from .base import repo_root, load_config
    root = os.getcwd() if a.cmd == "init" else repo_root()
    
    # Initialize context manager for v2.0
    from .context_manager import ContextManager
    context_manager = ContextManager(root)
    context = context_manager.get_context()
    
    # Pass context to command dispatch
    return dispatch_command(root, a, context)
```

### Phase 3: New Command Addition

**Objective**: Add v2.0 specific commands to CLI

**New Commands to Add**:
1. `cip interactive` - Enter interactive mode
2. `cip workflow <name>` - Run guided workflow
3. `cip suggest` - Get intelligent suggestions
4. `cip explain <command>` - Explain command with context
5. `cip plan <goal>` - Generate action plan

**Changes Required**:
- Add argparse subparsers in `setup_argument_parser()`
- Create handler functions for each command
- Add to dispatch table

**Implementation Steps**:
```python
# In lib/cipkg/cli.py::setup_argument_parser()
# Add v2.0 commands
ip = sub.add_parser("interactive", help="Enter intelligent interactive mode")
wp = sub.add_parser("workflow", help="Run guided workflow")
wp.add_argument("name", nargs="?", help="Workflow name")
wp.add_argument("--resume", action="store_true", help="Resume previous execution")
sp = sub.add_parser("suggest", help="Get intelligent suggestions")
sp.add_argument("--max", type=int, default=5, help="Maximum suggestions")
ep = sub.add_parser("explain", help="Explain command with context")
ep.add_argument("command", help="Command to explain")
pp = sub.add_parser("plan", help="Generate action plan for goal")
pp.add_argument("goal", help="Goal to plan for")
```

### Phase 4: Existing Command Adaptation

**Objective**: Add context-aware adaptation to existing commands

**Commands to Adapt**:
1. `cip audit` - Auto-add --diff for uncommitted changes
2. `cip search` - Auto-set context path, filter by file types
3. `cip sync` - Auto-add --include-uncommitted
4. `cip index` - Auto-add --force for stale index

**Approach**:
1. Wrap existing handlers with adaptation logic
2. Use command adapter framework
3. Add `--adapt` flag for testing
4. Maintain backward compatibility

**Changes Required**:
- Modify handler functions to use context
- Add adaptation logic before command execution
- Add `--no-adapt` flag for disabling

**Implementation Steps**:
```python
# In lib/cipkg/cli.py::handle_audit_command()
def handle_audit_command(root, args, context=None):
    """Handle audit command with context-aware adaptation."""
    from .command_adapter import adapt_command
    from .base import load_config
    
    config = load_config(root)
    adaptation_enabled = config.get('command_adaptation', {}).get('enabled', True)
    
    if adaptation_enabled and context and not getattr(args, 'no_adapt', False):
        context_dict = {
            'repo_type': context.repository.repo_type,
            'git_state': context.repository.git_state,
            'index_status': context.repository.index_status
        }
        adapted_result = adapt_command(root, 'audit', args.__dict__, context_dict, config)
        args = argparse.Namespace(**adapted_result['adapted_args'])
    
    # Original audit logic
    from .stack import audit as stack_audit
    if hasattr(args, 'file') and args.file:
        result = stack_audit.audit_file(root, args.file)
    elif hasattr(args, 'diff') and args.diff:
        result = stack_audit.audit_diff(root)
    else:
        result = stack_audit.audit(root, refresh=True)
    _out(result)
```

### Phase 5: Help System Integration

**Objective**: Integrate context-aware help with existing help system

**Approach**:
1. Add `--classic` flag to help command
2. Use context-aware help by default
3. Integrate suggestion display in help output

**Changes Required**:
- Modify help display logic
- Add context-aware help generation
- Update help command handler

**Implementation Steps**:
```python
# In lib/cipkg/cli.py
def handle_help_command(root, args, context=None):
    """Handle help command with context awareness."""
    classic = getattr(args, 'classic', False)
    
    if classic:
        # Show traditional help
        p = setup_argument_parser()
        p.print_help()
    else:
        # Show context-aware help
        from .help_system import display_help
        command = getattr(args, 'command', None)
        display_help(root, command, classic=False)
```

### Phase 6: Error Handling Integration

**Objective**: Wrap existing commands with error handling and recovery

**Approach**:
1. Add error handling wrapper to command dispatch
2. Use error detection and recovery system
3. Provide user-friendly error messages

**Changes Required**:
- Modify `dispatch_command()` to wrap with error handling
- Add error prevention checks
- Integrate with learning system

**Implementation Steps**:
```python
# In lib/cipkg/cli.py::dispatch_command()
def dispatch_command(root, args, context=None):
    """Dispatch command with error handling and recovery."""
    handler = handlers.get(args.cmd)
    if not handler:
        print("unknown command: %s" % args.cmd)
        return 1
    
    try:
        # Validate preconditions
        from .error_system import validate_preconditions
        validation = validate_preconditions(args.cmd, args.__dict__, root)
        if validation['warnings']:
            print("⚠️  Warnings:")
            for warning in validation['warnings']:
                print(f"  • {warning}")
        
        # Execute command with error handling
        return handler(root, args, context)
        
    except Exception as e:
        # Handle error with recovery
        from .error_system import handle_error_with_recovery
        result = handle_error_with_recovery(e, args.cmd, args.__dict__, root)
        
        if not result.get('recovered'):
            return 1
        return 0
```

### Phase 7: Learning System Integration

**Objective**: Record command executions for learning

**Approach**:
1. Record every command execution
2. Track user responses to suggestions
3. Update user profiles

**Changes Required**:
- Add learning recording to command dispatch
- Record suggestion accept/reject
- Update user profiles

**Implementation Steps**:
```python
# In lib/cipkg/cli.py::dispatch_command()
def dispatch_command(root, args, context=None):
    """Dispatch command with learning integration."""
    handler = handlers.get(args.cmd)
    if not handler:
        print("unknown command: %s" % args.cmd)
        return 1
    
    # Record command execution for learning
    try:
        from .learning_system import record_user_action
        record_user_action(
            root=root,
            action_type='command',
            user_id='default',
            repo_id=os.path.basename(root),
            command=args.cmd,
            arguments=args.__dict__,
            context=context.repository.__dict__ if context else {},
            success=True
        )
    except Exception:
        pass  # Don't fail if learning is unavailable
    
    # Execute command
    return handler(root, args, context)
```

### Phase 8: Interactive Mode Integration

**Objective**: Integrate interactive mode as primary v2.0 feature

**Approach**:
1. Add `cip interactive` command
2. Integrate with existing CLI infrastructure
3. Provide seamless transition between modes

**Changes Required**:
- Add interactive command handler
- Integrate with context manager
- Use existing command infrastructure

**Implementation Steps**:
```python
# In lib/cipkg/cli.py
def handle_interactive_command(root, args, context=None):
    """Handle interactive mode command."""
    from .interactive import start_interactive_mode
    start_interactive_mode(root)
```

## Backward Compatibility Strategy

### Configuration Compatibility
- **Existing configs**: Continue to work without modification
- **New configs**: Include v2.0 sections automatically
- **Migration**: Automatic migration on first v2.0 feature use

### Command Compatibility
-existing commands**: Work exactly as before
- **New behavior**: Opt-in via configuration or flags
- **Fallback**: Graceful degradation if v2.0 features unavailable

### Feature Flags
```toml
[interactive]
enabled = true  # Can be disabled for v1.0 behavior
mode = "hybrid"  # auto, interactive, hybrid

[command_adaptation]
enabled = true  # Can be disabled for original behavior
fallback_on_error = true  # Fallback to original on error
```

## Testing Strategy

### Unit Tests
- Test configuration merging logic
- Test context building
- Test command adaptation logic
- Test error handling and recovery

### Integration Tests
- Test new commands (interactive, workflow, suggest)
- Test adapted existing commands
- Test help system integration
- Test learning system recording

### Compatibility Tests
- Test v1.0 commands work unchanged
- Test existing configs work unchanged
- Test feature flags work correctly
- Test fallback behavior

## Implementation Order

### Priority 1: Core Infrastructure (Week 1)
1. Configuration integration
2. Context manager initialization
3. Error handling wrapper

### Priority 2: New Commands (Week 2)
1. Interactive command
2. Workflow command
3. Suggest command

### Priority 3: Command Adaptation (Week 3)
1. Audit command adaptation
2. Search command adaptation
3. Sync command adaptation

### Priority 4: Help Integration (Week 4)
1. Context-aware help
2. Classic help fallback
3. Suggestion display

### Priority 5: Learning Integration (Week 5)
1. Command execution recording
2. User profile updates
3. Pattern analysis

### Priority 6: Testing & Validation (Week 6)
1. Unit tests
2. Integration tests
3. Compatibility tests
4. Performance tests

## Risk Mitigation

### Configuration Conflicts
- **Risk**: v2.0 config conflicts with existing config
- **Mitigation**: Conservative merging, validation, fallback to v1.0

### Performance Impact
- **Risk**: Context building slows CLI startup
- **Mitigation**: Lazy loading, caching, background initialization

### Breaking Changes
- **Risk**: Existing commands behave differently
- **Mitigation**: Opt-in behavior, feature flags, extensive testing

### Learning System Overhead
- **Risk**: Learning system slows operations
- **Mitigation**: Async recording, minimal overhead, disable option

## Success Criteria

### Functional Requirements
- All existing commands work unchanged
- New commands work as designed
- Context-aware adaptations work correctly
- Interactive mode is functional
- Learning system records data

### Non-Functional Requirements
- CLI startup time < 2 seconds
- Context building < 1 second
- Error recovery success rate > 80%
- Learning system overhead < 50ms

### User Experience
- Smooth transition from v1.0 to v2.0
- Clear documentation for new features
- Intuitive interactive mode
- Helpful error messages

## Rollback Plan

### Immediate Rollback
- Disable v2.0 features via config
- Revert CLI changes if needed
- Restore v1.0 behavior

### Gradual Rollback
- Disable specific features individually
- Fallback to original command handlers
- Disable learning system

### Data Cleanup
- Remove v2.0 data directories
- Clean up learning data
- Restore original config structure

## Documentation Requirements

### User Documentation
- v2.0 features guide
- Interactive mode tutorial
- Workflow documentation
- Configuration reference

### Developer Documentation
- Integration architecture
- API documentation
- Extension guide
- Testing guide

### Migration Guide
- v1.0 to v2.0 migration
- Configuration migration
- Custom workflow creation
- Custom adapter creation

## Next Steps

1. **Review and approve** this integration plan
2. **Begin Phase 1** - Configuration integration
3. **Test each phase** before proceeding
4. **Gather user feedback** during implementation
5. **Iterate** based on feedback and testing

## Conclusion

This integration plan provides a systematic approach to incorporating v2.0 features into the existing CLI architecture while maintaining backward compatibility and minimizing disruption. The phased implementation allows for incremental testing and validation, reducing risk and ensuring a smooth transition for existing users.
