# CIP v1.2 — Pressure Test: 310 Atomic Scenarios

Solo dev / project owner questions the system should answer **immediately** from index alone.
Each mapped to a single CLI command. Gaps marked with `⚠️ GAP`.
Expanded from 100 → 310 with deep-dive pressure tests.

---

## A. "What is this?" — Code Understanding (1–15)

| # | Atomic Question | Command | Gap? |
|---|-----------------|---------|------|
| 1 | What does this file do? | `cip context <file>` | |
| 2 | What is this function/class? | `cip symbol <name>` | |
| 3 | What does this project use for X? | `cip search "X"` | |
| 4 | What's the main entry point? | `cip map` | |
| 5 | What are the top-level directories? | `cip map` | |
| 6 | What frameworks/languages is this? | `cip describe` | |
| 7 | What does this config file control? | `cip context <config>` | |
| 8 | What is this test testing? | `cip context <test_file>` | |
| 9 | What type does this variable/function return? | `cip symbol <name>` | |
| 10 | What does this error message mean? | `cip search "<error text>"` | |
| 11 | What's the project's package structure? | `cip map` | |
| 12 | What does this module export? | `cip symbol <module>` | |
| 13 | What's the purpose of this directory? | `cip summary <dir>` | |
| 14 | What does this hook/middleware do? | `cip search "<hook name>"` | |
| 15 | What are the naming conventions here? | `cip search "<pattern>"` | |

## B. "Where is...?" — Locating Things (16–30)

| # | Atomic Question | Command | Gap? |
|---|-----------------|---------|------|
| 16 | Where is X defined? | `cip symbol X` | |
| 17 | Where is X used? | `cip search X` + `cip graph <id>` | |
| 18 | Where is this API route? | `cip routes` | |
| 19 | Where is this Prisma model used? | `cip models` + `cip search <Model>` | |
| 20 | Where is this env var referenced? | `cip search "<ENV_VAR>"` | |
| 21 | Where is this component imported? | `cip graph <id>` | |
| 22 | Where is this type defined? | `cip symbol <TypeName>` | |
| 23 | Where is the database connection config? | `cip search "database\|prisma\|sqlite"` | |
| 24 | Where is authentication handled? | `cip search "auth\|session\|jwt"` | |
| 25 | Where is this CSS class used? | `cip search "<className>"` | |
| 26 | Where is this utility function? | `cip symbol <name>` | |
| 27 | Where is the middleware chain? | `cip search "middleware"` | |
| 28 | Where is rate limiting configured? | `cip search "rate\|throttle\|limit"` | |
| 29 | Where is logging done? | `cip search "console\.\|logger\.\|log\."` | |
| 30 | Where is this feature's code path? | `cip context "<feature description>"` | |

## C. "What breaks if...?" — Impact & Blast Radius (31–45)

| # | Atomic Question | Command | Gap? |
|---|-----------------|---------|------|
| 31 | What breaks if I change this function? | `cip impact <symbol>` | |
| 32 | What breaks if I delete this file? | `cip impact <file>` | |
| 33 | What breaks if I rename this module? | `cip impact <module>` + `cip graph <id>` | |
| 34 | What breaks if I remove this dependency? | `cip search "<dep>"` | |
| 35 | What breaks if I change this schema field? | `cip impact <field>` | |
| 36 | What breaks if I modify this API endpoint? | `cip impact <route>` | |
| 37 | What depends on this shared utility? | `cip graph <id>` | |
| 38 | What tests cover this function? | `cip graph <id>` (tested_by edges) | |
| 39 | What files are affected by changes since commit X? | `cip impact --ref <sha>` | |
| 40 | What's the riskiest file to change? | `cip hotspots` | |
| 41 | What was recently changed that might be unstable? | `cip hotspots` | |
| 42 | What are the co-change patterns? | `cip graph <file>` (co_change edges) | |
| 43 | What breaks if I upgrade package X? | `cip search "<package>"` | |
| 44 | What other code uses this DB table/model? | `cip models` + `cip search <Model>` | |
| 45 | What's the blast radius of a config change? | `cip impact <config_file>` | |

## D. "How does... work?" — Architecture & Flow (46–60)

| # | Atomic Question | Command | Gap? |
|---|-----------------|---------|------|
| 46 | How does the auth flow work? | `cip context "auth flow"` | |
| 47 | How does data flow from API to DB? | `cip context "request lifecycle"` | |
| 48 | How is error handling done? | `cip search "catch\|error\|Error"` | |
| 49 | How is state managed? | `cip search "state\|store\|context"` | |
| 50 | How are tests structured? | `cip map` + `cip search "describe\|it\|test"` | |
| 51 | How does the build pipeline work? | `cip search "webpack\|vite\|rollup\|build"` | |
| 52 | How is caching implemented? | `cip search "cache\|Cache\|memo"` | |
| 53 | How does the retry/fallback logic work? | `cip search "retry\|fallback\|backup"` | |
| 54 | How is configuration layered? | `cip search "config\|Config\|env"` | |
| 55 | How does the WebSocket/realtime work? | `cip search "socket\|WebSocket\|ws"` | |
| 56 | How is validation done? | `cip search "validate\|schema\|zod\|yup"` | |
| 57 | How does the deployment work? | `cip search "deploy\|Docker\|vercel"` | |
| 58 | How is background work handled? | `cip search "queue\|worker\|cron\|job"` | |
| 59 | How does the notification system work? | `cip search "notify\|email\|push"` | |
| 60 | How is versioning/releases managed? | `cip search "version\|release\|changelog"` | |

## E. "What's wrong?" — Quality & Health (61–75)

| # | Atomic Question | Command | Gap? |
|---|-----------------|---------|------|
| 61 | Are there any failing tests? | `cip broken` | |
| 62 | Are there type errors? | `cip broken` | |
| 63 | What's the test coverage like? | `cip search "coverage\|cover"` | ⚠️ GAP |
| 64 | What are the code quality findings? | `cip findings` | |
| 65 | What are the critical issues? | `cip findings --severity critical` | |
| 66 | Are there security vulnerabilities? | `cip audit` | |
| 67 | What quick-win refactors exist? | `cip refactors` | |
| 68 | Is the index fresh? | `cip verify` | |
| 69 | Is there index drift? | `cip verify` | |
| 70 | What's the overall code health score? | `cip doctor` | ⚠️ GAP (no score) |
| 71 | Are there dead/unused exports? | `cip search` + graph analysis | ⚠️ GAP |
| 72 | Are there circular dependencies? | `cip graph` with depth | ⚠️ GAP |
| 73 | What's the complexity hot spot? | `cip hotspots` | |
| 74 | Are there lint errors? | `cip broken` | |
| 75 | What's the doc coverage? | `cip search "TODO\|FIXME\|HACK"` | ⚠️ GAP |

## F. "What changed?" — History & Git (76–85)

| # | Atomic Question | Command | Gap? |
|---|-----------------|---------|------|
| 76 | Who last changed this file? | `cip history <file>` | |
| 77 | What changed in the last week? | `cip history <path>` | |
| 78 | What's the git blame for this line? | `cip history <file>` | ⚠️ GAP (no line-level) |
| 79 | What files change together? | `cip graph <file>` (co_change) | |
| 80 | What's the most-changed file? | `cip hotspots` | |
| 81 | What was the last deploy? | `cip history` | |
| 82 | What commit introduced this bug? | `cip history <file>` | ⚠️ GAP (no bisect) |
| 83 | What's the merge conflict risk? | `cip impact --ref <branch>` | ⚠️ GAP |
| 84 | What's the release history? | `cip history` | |
| 85 | What files were touched in this PR? | `cip impact --ref <base>` | |

## G. "What should I do?" — Decision Support (86–95)

| # | Atomic Question | Command | Gap? |
|---|-----------------|---------|------|
| 86 | Should I refactor this file? | `cip impact` + `cip findings` | |
| 87 | Which issue should I fix first? | `cip findings --severity critical` | |
| 88 | Is this feature worth building? | `cip impact` + `cip summary` | |
| 89 | What's the safest way to change this? | `cip impact <target>` | |
| 90 | What tests should I write first? | `cip graph <id>` (tested_by) | |
| 91 | Should I upgrade this dependency? | `cip search "<dep>"` | |
| 92 | Is this code ready to ship? | `cip gate` | |
| 93 | What's blocking the release? | `cip broken` + `cip gate` | |
| 94 | Where should I add logging? | `cip search "error\|catch"` | ⚠️ GAP |
| 95 | What needs documentation? | `cip summary` | |

## H. "Show me everything" — Bulk / Deep Queries (96–100)

| # | Atomic Question | Command | Gap? |
|---|-----------------|---------|------|
| 96 | Show me all API routes | `cip routes` | |
| 97 | Show me all DB models and their usage | `cip models` | |
| 98 | Show me the full dependency graph | `cip graph <id> --depth 3` | |
| 99 | Show me the project architecture | `cip map` + `cip summary` | |
| 100 | Give me a full health report | `cip doctor` + `cip audit` + `cip broken` | |

---

## Gap Summary

| Category | Total | Covered | Gaps | Gap IDs |
|----------|-------|---------|------|---------|
| A. Code Understanding | 15 | 15 | 0 | — |
| B. Locating Things | 15 | 15 | 0 | — |
| C. Impact & Blast Radius | 15 | 15 | 0 | — |
| D. Architecture & Flow | 15 | 15 | 0 | — |
| E. Quality & Health | 15 | 10 | 5 | 63,70,71,72,75 |
| F. History & Git | 10 | 6 | 4 | 78,79,82,83 |
| G. Decision Support | 10 | 8 | 2 | 94,95 |
| H. Bulk / Deep Queries | 5 | 5 | 0 | — |
| **TOTAL** | **100** | **89** | **11** | |

### Priority Gaps (what to build next)

1. **`cip coverage`** — test coverage integration (vitest/jest/pytest output ingestion)
2. **`cip dead`** — dead code / unused exports detection
3. **`cip circular`** — circular dependency detection
4. **`cip blame <file> <line>`** — git blame at line level
5. **`cip bisect <description>`** — git bisect helper
6. **`cip score`** — overall health score (0–100)
7. **`cip docs`** — documentation coverage report

---

## I. "How fast is...?" — Performance & Cost (101–115)

| # | Atomic Question | Command | Gap? |
|---|-----------------|---------|------|
| 101 | What's the slowest function? | `cip hotspots` | ⚠️ GAP (no perf data) |
| 102 | What's the biggest file? | `cip map` | |
| 103 | What has the most dependencies? | `cip graph <id>` | ⚠️ GAP (no dep count) |
| 104 | What's the heaviest import chain? | `cip graph <id> --depth 3` | ⚠️ GAP (no depth cost) |
| 105 | What uses the most tokens in context? | `cip context` | |
| 106 | What's the embedding cost per sync? | `cip doctor` | ⚠️ GAP |
| 107 | What's the index DB size? | `cip doctor` | ⚠️ GAP (no size) |
| 108 | What's the bundle size impact of adding X? | `cip impact <file>` | ⚠️ GAP |
| 109 | What's the cold start path? | `cip context "startup\|init\|bootstrap"` | |
| 110 | What's the most expensive query? | `cip search "query\|find\|select"` | ⚠️ GAP |
| 111 | What's the memory footprint? | — | ⚠️ GAP |
| 112 | What's the API response time? | — | ⚠️ GAP |
| 113 | What's the database query count? | `cip search "prisma\.\|findMany\|findFirst"` | ⚠️ GAP |
| 114 | What's the cache hit rate? | `cip search "cache"` | ⚠️ GAP |
| 115 | What's the Lighthouse score? | — | ⚠️ GAP |

## J. "Is it safe?" — Security Deep Dive (116–130)

| # | Atomic Question | Command | Gap? |
|---|-----------------|---------|------|
| 116 | Where are secrets stored? | `cip search "secret\|key\|token\|password"` | |
| 117 | Are there hardcoded credentials? | `cip audit` | |
| 118 | Where is user input handled? | `cip search "req.body\|req.query\|input"` | |
| 119 | Is input sanitized? | `cip search "sanitize\|escape\|xss"` | ⚠️ GAP (no sanitization check) |
| 120 | Where is SQL constructed? | `cip search "query\|\$\{.*\}"` | |
| 121 | Is there SQL injection risk? | `cip audit` | |
| 122 | Where is CORS configured? | `cip search "cors\|CORS"` | |
| 123 | Where is CSP configured? | `cip search "Content-Security-Policy\|CSP"` | |
| 124 | Where is rate limiting? | `cip search "rate\|throttle\|limit"` | |
| 125 | Where is auth enforced? | `cip search "auth\|session\|middleware"` | |
| 126 | Are there unprotected routes? | `cip routes` + `cip search "auth"` | ⚠️ GAP |
| 127 | Where is encryption done? | `cip search "encrypt\|decrypt\|hash\|bcrypt"` | |
| 128 | Where is TLS enforced? | `cip search "https\|tls\|ssl"` | |
| 129 | Are there any eval() calls? | `cip search "eval\|Function\|exec"` | |
| 130 | Where is file upload handled? | `cip search "upload\|multer\|formidable"` | |

## K. "What's the data model?" — Database Deep Dive (131–145)

| # | Atomic Question | Command | Gap? |
|---|-----------------|---------|------|
| 131 | What tables/models exist? | `cip models` | |
| 132 | What are the relationships? | `cip models` | ⚠️ GAP (no relation map) |
| 133 | Where is each model created? | `cip search "create\|insert\|save"` | |
| 134 | Where is each model read? | `cip search "find\|select\|get"` | |
| 135 | Where is each model updated? | `cip search "update\|modify\|set"` | |
| 136 | Where is each model deleted? | `cip search "delete\|remove\|destroy"` | |
| 137 | What migrations exist? | `cip search "migration\|migrate\|schema"` | ⚠️ GAP |
| 138 | What's the schema diff? | — | ⚠️ GAP |
| 139 | Where is seeding done? | `cip search "seed\|fixture\|mock"` | |
| 140 | What's the N+1 risk? | `cip audit` | |
| 141 | Where are transactions used? | `cip search "transaction\|$transaction"` | |
| 142 | What indexes exist? | — | ⚠️ GAP |
| 143 | What's the query pattern? | `cip search "findMany\|findFirst\|groupBy"` | |
| 144 | Where is connection pooling? | `cip search "pool\|Pool\|connection"` | |
| 145 | What's the data retention policy? | `cip search "expire\|delete.*where\|retention"` | ⚠️ GAP |

## L. "How does the API work?" — API Deep Dive (146–160)

| # | Atomic Question | Command | Gap? |
|---|-----------------|---------|------|
| 146 | What endpoints exist? | `cip routes` | |
| 147 | What methods are supported? | `cip routes` | ⚠️ GAP (no method detail) |
| 148 | What's the request schema? | `cip search "zod\|schema\|validate"` | |
| 149 | What's the response schema? | `cip search "response\|json\|res\."` | ⚠️ GAP |
| 150 | What's the error format? | `cip search "error\|status\|statusCode"` | |
| 151 | Where is pagination? | `cip search "page\|offset\|cursor\|skip"` | |
| 152 | Where is filtering? | `cip search "filter\|where\|query"` | |
| 153 | Where is sorting? | `cip search "sort\|order\|orderBy"` | |
| 154 | Where is field selection? | `cip search "select\|fields\|include"` | |
| 155 | What's the auth middleware chain? | `cip graph <auth_symbol>` | |
| 156 | Where is request logging? | `cip search "log.*req\|morgan\|logger"` | |
| 157 | Where is CORS configured per route? | `cip search "cors"` | ⚠️ GAP |
| 158 | What's the rate limit per route? | `cip search "rate\|limit"` | ⚠️ GAP |
| 159 | Where is versioning? | `cip search "version\|v1\|v2\|api/"` | |
| 160 | What's the OpenAPI spec? | `cip search "swagger\|openapi"` | ⚠️ GAP |

## M. "What about the frontend?" — Frontend Deep Dive (161–175)

| # | Atomic Question | Command | Gap? |
|---|-----------------|---------|------|
| 161 | What components exist? | `cip search "export.*function\|export.*const"` | |
| 162 | What's the component tree? | `cip graph <app_symbol>` | ⚠️ GAP (no tree) |
| 163 | Where is state managed? | `cip search "useState\|useReducer\|zustand\|redux"` | |
| 164 | Where are side effects? | `cip search "useEffect\|useLayoutEffect"` | |
| 165 | Where is data fetched? | `cip search "fetch\|axios\|swr\|query"` | |
| 166 | What's the routing structure? | `cip routes` | |
| 167 | Where are forms handled? | `cip search "form\|Form\|onSubmit"` | |
| 168 | Where is validation? | `cip search "validate\|schema\|zod"` | |
| 169 | Where are error boundaries? | `cip search "ErrorBoundary\|error.*boundary"` | |
| 170 | Where is loading state? | `cip search "loading\|isLoading\|skeleton"` | |
| 171 | Where is accessibility? | `cip search "aria-\|role=\|alt="` | |
| 172 | Where is responsive design? | `cip search "@media\|breakpoint\|responsive"` | |
| 173 | Where are animations? | `cip search "animation\|transition\|motion"` | |
| 174 | Where is theming? | `cip search "theme\|color\|dark\|light"` | |
| 175 | What's the CSS strategy? | `cip search "tailwind\|css\|styled\|module"` | |

## N. "How does background work?" — Async & Workers (176–190)

| # | Atomic Question | Command | Gap? |
|---|-----------------|---------|------|
| 176 | What queues exist? | `cip search "queue\|Queue\|bull\|bee"` | ⚠️ GAP |
| 177 | What workers process jobs? | `cip search "worker\|Worker\|process"` | |
| 178 | What cron jobs run? | `cip search "cron\|schedule\|setInterval"` | |
| 179 | What's the job retry logic? | `cip search "retry\|backoff\|attempts"` | |
| 180 | What's the dead letter queue? | `cip search "dead.*letter\|DLQ\|failed"` | ⚠️ GAP |
| 181 | Where is job logging? | `cip search "log.*job\|log.*task"` | |
| 182 | What's the concurrency limit? | `cip search "concurrency\|parallel\|worker"` | ⚠️ GAP |
| 183 | What's the job priority? | `cip search "priority\|urgent\|critical"` | ⚠️ GAP |
| 184 | Where is webhook handling? | `cip search "webhook\|hook\|callback"` | |
| 185 | What's the event bus? | `cip search "event\|Event\|emit\|on\(")` | |
| 186 | Where is pub/sub? | `cip search "publish\|subscribe\|channel"` | |
| 187 | What's the WebSocket handler? | `cip search "socket\|ws\|websocket"` | |
| 188 | Where is file processing? | `cip search "upload\|file\|read\|write"` | |
| 189 | Where is image processing? | `cip search "sharp\|jimp\|image\|resize"` | |
| 190 | Where is email sending? | `cip search "email\|mail\|smtp\|sendgrid"` | |

## O. "What's the deployment?" — DevOps Deep Dive (191–205)

| # | Atomic Question | Command | Gap? |
|---|-----------------|---------|------|
| 191 | What's the Docker setup? | `cip search "docker\|Dockerfile\|docker-compose"` | |
| 192 | What's the CI/CD pipeline? | `cip search "github.*action\|workflow\|pipeline"` | ⚠️ GAP |
| 193 | What's the build command? | `cip search "build\|compile\|tsc\|next build"` | |
| 194 | What's the start command? | `cip search "start\|serve\|node\|deno"` | |
| 195 | What env vars are required? | `cip search "process.env\|import.meta.env"` | |
| 196 | What's the health check? | `cip search "health\|alive\|ready\|ping"` | |
| 197 | What's the graceful shutdown? | `cip search "shutdown\|SIGTERM\|SIGINT\|close"` | |
| 198 | What's the logging strategy? | `cip search "log\|logger\|winston\|pino"` | |
| 199 | What's the monitoring setup? | `cip search "monitor\|metric\|prometheus\|datadog"` | ⚠️ GAP |
| 200 | What's the alerting config? | `cip search "alert\|pagerduty\|slack.*alert"` | ⚠️ GAP |
| 201 | What's the backup strategy? | `cip search "backup\|dump\|snapshot"` | ⚠️ GAP |
| 202 | What's the rollback plan? | `cip search "rollback\|revert\|undo"` | ⚠️ GAP |
| 203 | What's the scaling config? | `cip search "scale\|replica\|instance\|autoscal"` | ⚠️ GAP |
| 204 | What's the CDN setup? | `cip search "cdn\|cloudfront\|cloudflare"` | ⚠️ GAP |
| 205 | What's the SSL config? | `cip search "ssl\|cert\|tls\|https"` | |

## P. "What patterns are used?" — Code Patterns (206–220)

| # | Atomic Question | Command | Gap? |
|---|-----------------|---------|------|
| 206 | What design patterns are used? | `cip search "factory\|singleton\|observer\|strategy"` | ⚠️ GAP (no pattern detection) |
| 207 | What's the error handling pattern? | `cip search "try\|catch\|throw\|Error"` | |
| 208 | What's the logging pattern? | `cip search "console\.\|log\.\|logger\."` | |
| 209 | What's the config pattern? | `cip search "config\|Config\|env\|ENV"` | |
| 210 | What's the dependency injection? | `cip search "inject\|Inject\|provider\|Provider"` | |
| 211 | What's the middleware pattern? | `cip search "middleware\|use\|next\(\)"` | |
| 212 | What's the validation pattern? | `cip search "validate\|schema\|parse"` | |
| 213 | What's the serialization? | `cip search "serialize\|JSON\|parse\|stringify"` | |
| 214 | What's the caching pattern? | `cip search "cache\|Cache\|memo\|memoize"` | |
| 215 | What's the retry pattern? | `cip search "retry\|attempt\|backoff"` | |
| 216 | What's the circuit breaker? | `cip search "circuit\|breaker\|fallback"` | |
| 217 | What's the rate limit pattern? | `cip search "rate\|limit\|throttle\|bucket"` | |
| 218 | What's the pagination pattern? | `cip search "page\|offset\|cursor\|limit"` | |
| 219 | What's the filter pattern? | `cip search "filter\|where\|query\|search"` | |
| 220 | What's the sort pattern? | `cip search "sort\|order\|orderBy\|compare"` | |

## Q. "What about testing?" — Testing Deep Dive (221–235)

| # | Atomic Question | Command | Gap? |
|---|-----------------|---------|------|
| 221 | What test framework is used? | `cip search "describe\|it\|test\|expect"` | |
| 222 | What's the test file naming? | `cip search "\.test\.\|\.spec\.\|_test\."` | |
| 223 | What's the test directory structure? | `cip map` | |
| 224 | What's the mocking pattern? | `cip search "mock\|Mock\|jest.fn\|vi.fn"` | |
| 225 | What's the fixture pattern? | `cip search "fixture\|Factory\|build\|create"` | |
| 226 | What's the snapshot testing? | `cip search "toMatchSnapshot\|toMatchInlineSnapshot"` | |
| 227 | What's the E2E setup? | `cip search "playwright\|cypress\|e2e"` | |
| 228 | What's the unit test ratio? | `cip search "\.test\.\|\.spec\."` | ⚠️ GAP (no ratio) |
| 229 | What's the coverage threshold? | `cip search "coverage\|threshold\|coverageThreshold"` | ⚠️ GAP |
| 230 | What's the test data strategy? | `cip search "seed\|factory\|fixture\|mock"` | |
| 231 | What's the test isolation? | `cip search "beforeEach\|afterEach\|beforeAll\|afterAll"` | |
| 232 | What's the async test pattern? | `cip search "async\|await\|done\(\)\|resolves"` | |
| 233 | What's the error test pattern? | `cip search "toThrow\|rejects\|catch\|error"` | |
| 234 | What's the integration test pattern? | `cip search "integration\|e2e\|end.to.end"` | |
| 235 | What's the performance test? | `cip search "benchmark\|perf\|performance\|stress"` | ⚠️ GAP |

## R. "What about docs?" — Documentation Deep Dive (236–250)

| # | Atomic Question | Command | Gap? |
|---|-----------------|---------|------|
| 236 | What README sections exist? | `cip summary README.md` | |
| 237 | What's documented? | `cip summary` | |
| 238 | What's undocumented? | — | ⚠️ GAP |
| 239 | Where are code comments? | `cip search "//\|/\*\|#.*comment"` | ⚠️ GAP |
| 240 | Where are TODOs? | `cip search "TODO\|FIXME\|HACK\|XXX"` | |
| 241 | Where are FIXMEs? | `cip search "FIXME"` | |
| 242 | Where are HACKs? | `cip search "HACK\|WORKAROUND\|kludge"` | |
| 243 | What's the API doc? | `cip search "swagger\|openapi\|api.*doc"` | |
| 244 | What's the JSDoc coverage? | `cip search "\*\*\|@param\|@returns"` | ⚠️ GAP |
| 245 | What's the inline doc style? | `cip search "//\|/\*\|#" | ⚠️ GAP |
| 246 | What's the changelog format? | `cip search "changelog\|CHANGELOG\|release"` | |
| 247 | What's the contributing guide? | `cip search "CONTRIBUTING\|contributing"` | |
| 248 | What's the license? | `cip search "license\|LICENSE\|MIT\|Apache"` | |
| 249 | What's the architecture doc? | `cip search "architecture\|ARCHITECTURE\|design"` | ⚠️ GAP |
| 250 | What's the ADR format? | `cip search "decision\|ADR\|RFC\|proposal"` | ⚠️ GAP |

## S. "What about migrations?" — Migration & Upgrade (251–265)

| # | Atomic Question | Command | Gap? |
|---|-----------------|---------|------|
| 251 | What DB migrations exist? | `cip search "migration\|migrate\|prisma.*migrate"` | ⚠️ GAP |
| 252 | What's the migration order? | `cip search "migration\|migrate"` | ⚠️ GAP |
| 253 | What's the rollback migration? | `cip search "rollback\|revert\|down"` | ⚠️ GAP |
| 254 | What's the schema change risk? | `cip impact <migration_file>` | |
| 255 | What's the data migration? | `cip search "data.*migration\|transform\|convert"` | ⚠️ GAP |
| 256 | What's the breaking change? | `cip search "breaking\|deprecated\|removed"` | ⚠️ GAP |
| 257 | What's the API versioning? | `cip search "version\|v1\|v2\|api.*v"` | |
| 258 | What's the deprecation policy? | `cip search "deprecated\|@deprecated\|remove.*later"` | |
| 259 | What's the upgrade path? | `cip search "upgrade\|update\|migrate"` | |
| 260 | What's the dependency update? | `cip search "update\|upgrade\|bump\|version"` | |
| 261 | What's the lockfile? | `cip search "lock\|package-lock\|yarn.lock\|pnpm-lock"` | |
| 262 | What's the peer dependency? | `cip search "peer\|peerDep\|peerDependency"` | |
| 263 | What's the compatibility matrix? | — | ⚠️ GAP |
| 264 | What's the Node.js version? | `cip search "node\|engine\|version.*node"` | |
| 265 | What's the TypeScript version? | `cip search "typescript\|ts.version\|compilerOptions"` | |

## T. "What about monitoring?" — Observability (266–280)

| # | Atomic Question | Command | Gap? |
|---|-----------------|---------|------|
| 266 | What's logged? | `cip search "log\|logger\|console\."` | |
| 267 | What's the log level? | `cip search "log.*level\|debug\|info\|warn\|error"` | ⚠️ GAP |
| 268 | What's the structured logging? | `cip search "JSON.*log\|structured\|pino\|winston"` | ⚠️ GAP |
| 269 | What's the metrics collection? | `cip search "metric\|counter\|gauge\|histogram"` | ⚠️ GAP |
| 270 | What's the tracing setup? | `cip search "trace\|span\|opentelemetry\|jaeger"` | ⚠️ GAP |
| 271 | What's the error tracking? | `cip search "sentry\|bugsnag\|error.*track"` | |
| 272 | What's the APM setup? | `cip search "apm\|new.relic\|datadog\|elastic"` | ⚠️ GAP |
| 273 | What's the health endpoint? | `cip search "health\|alive\|ready\|status"` | |
| 274 | What's the readiness probe? | `cip search "readiness\|ready\|probe"` | ⚠️ GAP |
| 275 | What's the liveness probe? | `cip search "liveness\|alive\|probe"` | ⚠️ GAP |
| 276 | What's the dashboard? | `cip dashboard` | |
| 277 | What's the alert rule? | `cip search "alert\|threshold\|critical"` | ⚠️ GAP |
| 278 | What's the log aggregation? | `cip search "elasticsearch\|fluentd\|logstash"` | ⚠️ GAP |
| 279 | What's the sampling rate? | `cip search "sample\|sampling\|rate"` | ⚠️ GAP |
| 280 | What's the correlation ID? | `cip search "correlation\|request.*id\|trace.*id"` | ⚠️ GAP |

## U. "What about features?" — Feature Management (281–295)

| # | Atomic Question | Command | Gap? |
|---|-----------------|---------|------|
| 281 | What feature flags exist? | `cip search "feature.*flag\|toggle\|featureFlag"` | ⚠️ GAP |
| 282 | What's the feature toggle pattern? | `cip search "isEnabled\|isActive\|check"` | ⚠️ GAP |
| 283 | What's the A/B test setup? | `cip search "ab.*test\|experiment\|variant"` | ⚠️ GAP |
| 284 | What's the rollout strategy? | `cip search "rollout\|gradual\|canary\|percent"` | ⚠️ GAP |
| 285 | What's the kill switch? | `cip search "kill.*switch\|emergency\|disable"` | ⚠️ GAP |
| 286 | What's the feature request flow? | — | ⚠️ GAP |
| 287 | What's the roadmap? | — | ⚠️ GAP |
| 288 | What's the release notes? | `cip search "release\|changelog\|what.*new"` | |
| 289 | What's the version numbering? | `cip search "semver\|version\|major\|minor\|patch"` | |
| 290 | What's the release cadence? | `cip history` | ⚠️ GAP (no cadence) |
| 291 | What's the hotfix process? | `cip search "hotfix\|urgent\|critical\|patch"` | ⚠️ GAP |
| 292 | What's the feature branch? | `cip search "feature\|feat\|branch"` | |
| 293 | What's the code freeze? | — | ⚠️ GAP |
| 294 | What's the release checklist? | — | ⚠️ GAP |
| 295 | What's the post-mortem process? | `cip search "postmortem\|incident\| RCA"` | ⚠️ GAP |

## V. "What about scaling?" — Scaling & Architecture (296–310)

| # | Atomic Question | Command | Gap? |
|---|-----------------|---------|------|
| 296 | What's the horizontal scale path? | — | ⚠️ GAP |
| 297 | What's the vertical scale path? | — | ⚠️ GAP |
| 298 | What's the stateless components? | `cip search "state\|session\|cache"` | ⚠️ GAP |
| 299 | What's the stateful components? | `cip search "session\|store\|database"` | ⚠️ GAP |
| 300 | What's the shared state risk? | `cip search "global\|singleton\|static"` | ⚠️ GAP |
| 301 | What's the database sharding? | — | ⚠️ GAP |
| 302 | What's the read replica? | `cip search "replica\|read.*replica\|follower"` | ⚠️ GAP |
| 303 | What's the cache layer? | `cip search "cache\|redis\|memcache\|lru"` | |
| 304 | What's the CDN strategy? | `cip search "cdn\|static\|asset\|public"` | |
| 305 | What's the API gateway? | `cip search "gateway\|proxy\|nginx\|traefik"` | ⚠️ GAP |
| 306 | What's the service mesh? | `cip search "mesh\|istio\|linkerd\|envoy"` | ⚠️ GAP |
| 307 | What's the event sourcing? | `cip search "event.*store\|event.*sourcing\|append"` | ⚠️ GAP |
| 308 | What's the CQRS setup? | `cip search "command.*query\|read.*model\|write.*model"` | ⚠️ GAP |
| 309 | What's the microservice boundary? | `cip map` | ⚠️ GAP (no boundary) |
| 310 | What's the API contract? | `cip search "contract\|schema\|interface\|type"` | |

---

## Updated Gap Summary

| Category | Total | Covered | Gaps | New Gaps |
|----------|-------|---------|------|----------|
| I. Performance & Cost | 15 | 3 | 12 | 101–108,110–115 |
| J. Security Deep Dive | 15 | 10 | 5 | 119,126,129,130 |
| K. Database Deep Dive | 15 | 7 | 8 | 132,137,138,141,143,145 |
| L. API Deep Dive | 15 | 9 | 6 | 147,149,151,156,158,160 |
| M. Frontend Deep Dive | 15 | 11 | 4 | 162,171,173,175 |
| N. Async & Workers | 15 | 7 | 8 | 176,180,182,183,187,189,190 |
| O. DevOps Deep Dive | 15 | 5 | 10 | 192,199,200,201,202,203,204 |
| P. Code Patterns | 15 | 12 | 3 | 206,213,220 |
| Q. Testing Deep Dive | 15 | 11 | 4 | 224,228,229,235 |
| R. Documentation | 15 | 7 | 8 | 238,243,244,245,249,250 |
| S. Migration & Upgrade | 15 | 5 | 10 | 251–258,262,265 |
| T. Observability | 15 | 3 | 12 | 267–280 |
| U. Feature Management | 15 | 2 | 13 | 281–295 |
| V. Scaling & Architecture | 15 | 2 | 13 | 296–310 |
| **TOTAL** | **310** | **210** | **100** | |

### Top Priority Gaps (build these first)

1. **`cip coverage`** — test coverage integration
2. **`cip dead`** — dead code detection
3. **`cip circular`** — circular dependency detection
4. **`cip blame <file> [line]`** — git blame
5. **`cip score`** — overall health score
6. **`cip migrations`** — DB migration inventory
7. **`cip env`** — env var inventory
8. **`cip logs`** — log pattern analysis
9. **`cip metrics`** — metrics collection status
10. **`cip features`** — feature flag inventory
11. **`cip deps`** — dependency graph + audit
12. **`cip api`** — API contract inventory
