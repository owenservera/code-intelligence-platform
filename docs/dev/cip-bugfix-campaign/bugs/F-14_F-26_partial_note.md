# F-14-partial / F-26-partial: Recovery Stubs — Manual Note

**Finding:** Recovery stubs and fake success states in error handling
**Level:** Manual (behavioral tracing required)
**Status:** Note-only — requires runtime behavior analysis

## Assessment

Recovery stubs (placeholder error handlers that return fake success) are a behavioral pattern that requires runtime tracing to detect:

1. **Context-dependent:** Whether a stub is appropriate depends on the error context and system state
2. **False positives:** Legitimate fallback mechanisms may look like stubs
3. **Runtime-only:** These patterns only manifest during execution, not in static analysis

## Specific Findings

- **F-14:** Partial recovery mechanisms in workflow/adapter layers
- **F-26:** Partial recovery in file ingestion/parsing

## Recommendation

- Audit recovery paths manually for critical workflows
- Add logging to distinguish legitimate fallbacks from stubs
- Consider adding runtime probes to detect when stubs are exercised
- Document expected recovery behavior in design docs
- No automated detector recommended — requires behavioral tracing
