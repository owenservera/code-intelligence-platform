# CORE-53: Hardcoded Confidences — Manual Note

**Finding:** Hardcoded confidence scores in ranking/scoring logic
**Level:** Manual (wording/intent analysis required)
**Status:** Note-only — requires domain knowledge

## Assessment

Hardcoded confidence scores are a design choice that requires understanding the intended behavior:

1. **Domain-specific:** Appropriate confidence thresholds vary by use case and data quality
2. **Tuning parameter:** These are often hyperparameters that should be tuned empirically
3. **Not a bug:** Hardcoded values are not inherently wrong — they reflect design decisions

## Specific Finding

- **CORE-53:** Hardcoded confidence values in ranking/scoring functions

## Recommendation

- Review hardcoded values to ensure they match intended behavior
- Consider making confidence scores configurable via settings
- Document the rationale for specific threshold choices
- Add comments explaining the trade-offs
- No automated detector recommended — this is a design decision, not a bug
