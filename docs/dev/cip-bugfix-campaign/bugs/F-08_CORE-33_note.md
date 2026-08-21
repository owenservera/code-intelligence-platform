# F-08 / CORE-33: Semantic Recall — Manual Note

**Finding:** Semantic recall quality (search relevance beyond lexical match)
**Level:** Manual (not automatable)
**Status:** Note-only — requires human evaluation

## Assessment

Semantic recall is fundamentally a quality-of-result metric that requires human judgment to assess whether search results are semantically relevant to the query. This cannot be automated with high confidence because:

1. **Subjective relevance:** What constitutes a "good" semantic match depends on context and user intent
2. **Domain-specific:** Semantic relevance varies across codebases and domains
3. **No ground truth:** Unlike syntax errors or undefined names, there is no binary correct/incorrect answer

## Recommendation

- Track semantic recall qualitatively through user feedback and manual evaluation
- Consider A/B testing different embedding models or chunking strategies
- Document expected behavior for specific query types in repo-specific guides
- No automated detector recommended — this is a human-in-the-loop quality metric
