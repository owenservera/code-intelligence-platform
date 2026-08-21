# CIP → Vivim Integration Guide

## Capability Resolution Integration

CIP's `route_for_agent()` now returns capability-scoped tool names compatible with Vivim's Capability Resolution Engine.

### Integration Pattern

When integrating CIP with Vivim's Capability Resolution Engine:

1. **Register CIP as a provider** in `seeds/providers/manifests.ts`:
   ```typescript
   {
     slug: "code-intelligence",
     category: "code-intelligence",
     capabilities: [
       "cap:code:search",
       "cap:code:symbol", 
       "cap:code:impact",
       "cap:code:context",
       "cap:code:audit",
       "cap:code:broken",
       "cap:code:graph",
       "cap:code:models",
       "cap:code:routes",
       "cap:code:migrations",
       "cap:code:coverage",
       "cap:code:dead",
       "cap:code:circular",
       "cap:code:map",
       "cap:code:summary",
       "cap:code:hotspots"
     ]
   }
   ```

2. **Wire confidence scores** through Vivim's existing confidence pipeline:
   ```typescript
   const cipRouting = route_for_agent(userQuery, context);
   for (const suggestion of cipRouting.suggestions) {
     capabilityEngine.registerCapability({
       id: suggestion.tool,
       confidence: suggestion.confidence,
       rationale: suggestion.rationale,
       category: suggestion.category
     });
   }
   ```

3. **MCP Server Integration**: CIP's MCP server (`cip mcp`) can be registered as a stdio MCP provider exposing the same capabilities.

### Capability Categories

All CIP capabilities are under the `code-intelligence` category:
- **Search & Discovery**: `cap:code:search`, `cap:code:symbol`, `cap:code:context`
- **Impact Analysis**: `cap:code:impact`, `cap:code:broken`, `cap:code:graph`
- **Schema & Models**: `cap:code:models`, `cap:code:migrations`
- **Architecture**: `cap:code:map`, `cap:code:summary`, `cap:code:hotspots`
- **Quality**: `cap:code:audit`, `cap:code:coverage`, `cap:code:dead`, `cap:code:circular`

### Example Usage

```typescript
// User query: "why is auth broken"
const routing = route_for_agent("why is auth broken");
// Returns:
// {
//   suggestions: [
//     {
//       tool: "cap:code:broken",
//       confidence: 0.9,
//       rationale: "Query asks about failing/error state",
//       category: "code-intelligence"
//     },
//     {
//       tool: "cap:code:impact", 
//       confidence: 0.85,
//       rationale: "After broken check, analyze impact",
//       category: "code-intelligence"
//     }
//   ]
// }
```

This integrates seamlessly with Vivim's existing capability resolution system.
