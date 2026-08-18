import { getActiveProject } from '@/stores/app'

const BASE = '/api'

// SPEC-19 §6.2: registry-level endpoints never take ?repo= (the middleware would
// only set a root if the value is a registered id, but the endpoints themselves
// ignore it — keep the wire free of noise and the intent explicit).
// /onboarding is NOT excluded: its gate usage (no path) must scope ?repo= to the
// ACTIVE project (GAP-06); the arbitrary-folder usage passes ?path=, which the
// backend prioritizes over the active root.
const NO_REPO_PREFIXES = ['/projects']

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const repo = getActiveProject()
  let url = `${BASE}${path}`
  const headers: Record<string, string> = { 'Content-Type': 'application/json' }
  if (repo && !NO_REPO_PREFIXES.some((p) => path.startsWith(p))) {
    const sep = url.includes('?') ? '&' : '?'
    url = `${url}${sep}repo=${encodeURIComponent(repo)}`
    headers['X-CIP-Project'] = repo
  }
  const res = await fetch(url, {
    headers,
    ...init,
  })
  const body = await res.json().catch(() => ({}))
  const env = body as { ok?: boolean; data?: T; error?: { message?: string } }
  // Backend always wraps success in {ok, data} and failure in {ok:false, error:{code,message}}.
  if (!res.ok || env.ok === false) {
    throw new Error(env.error?.message ?? `HTTP ${res.status}`)
  }
  // Unwrap the payload envelope so views read top-level fields (stable shape: SPEC-15 §4).
  return 'data' in env ? (env.data as T) : (body as T)
}

export interface StatusResponse {
  ok: boolean
  repo_root: string
  daemon: { running: boolean; pid: number | null; uptime: string | null }
  index: { fresh: boolean; last_sync: string | null; file_count: number }
  embedder: { backend: string; ready: boolean; warming: boolean }
}

export interface CommandInfo {
  name: string
  description: string
  category: string
  params: CommandParam[]
  label?: string
  priority?: string
  long_running?: boolean
  requires_confirmation?: boolean
}

export interface CommandParam {
  name: string
  type: 'string' | 'int' | 'float' | 'boolean'
  required: boolean
  default?: unknown
  help?: string
  choices?: unknown[]
}

export interface CommandCategory {
  name: string
  commands: CommandInfo[]
}

export interface CommandCatalog {
  categories: CommandCategory[]
}

export type JobEventType =
  | 'job.start'
  | 'job.progress'
  | 'job.log'
  | 'job.done'
  | 'job.error'
  | 'job.cancelled'
  | 'index.update'
  | 'watch.event'
  | 'file.changed'
  | 'quality.update'
  | 'memory.updated'
  | 'config.update'
  | 'verify.done'
  | 'signals.ingested'
  | 'workflow.step'
  | 'daemon.status'
  | 'vis.refresh'
  | 'event'
  | 'hello'
  | 'pong'

export interface JobProgressData {
  phase?: string
  current?: number
  total?: number
  pct?: number
  message?: string
}

export interface JobEvent {
  type: JobEventType
  job_id?: string
  command?: string
  data: unknown
  timestamp?: number
}

export interface JobInfo {
  id: string
  command: string
  status: 'running' | 'done' | 'error' | 'cancelled'
  started: number
  finished?: number
  error?: string
  result?: unknown
  logs: string[]
  params?: Record<string, unknown>
  pct: number
  phase?: string
}

export const jobApi = {
  list: (limit = 50) => request<{ jobs: JobInfo[]; count: number }>(`/jobs?limit=${limit}`),
  get: (id: string) => request<JobInfo>(`/jobs/${id}`),
  run: (cmd: string, params: Record<string, unknown> = {}) =>
    request<{ job_id: string; status: string }>(`/run`, {
      method: 'POST',
      body: JSON.stringify({ command: cmd, params }),
    }),
  cancel: (id: string) =>
    request<{ cancelled: boolean }>(`/jobs/${id}/cancel`, { method: 'POST' }),
}

export const eventsApi = {
  feed: (kind?: string, since?: number, limit = 100) => {
    const p = new URLSearchParams()
    if (kind) p.set('kind', kind)
    if (since !== undefined) p.set('since', String(since))
    p.set('limit', String(limit))
    return request<{ events: { ts: number; kind: string; payload: unknown }[]; count: number }>(
      `/events?${p.toString()}`,
    )
  },
}

export const api = {
  getStatus: () => request<StatusResponse>('/status'),
  getConfig: () => request<Record<string, unknown>>('/config'),
  getCommands: () => request<CommandCatalog>('/commands'),
  runCommand: (cmd: string, params: Record<string, unknown>) =>
    request<{ job_id: string; status: string }>(`/run`, {
      method: 'POST',
      body: JSON.stringify({ command: cmd, params }),
    }),
  cancelJob: (jobId: string) =>
    request<void>(`/jobs/${jobId}/cancel`, { method: 'POST' }),
}

// ── SPEC-03: Daemon & Server Management ──────────────────────────────────────
export interface DaemonStatus {
  pid: number | null
  port: number | null
  alive: boolean
  warm: boolean
  health: {
    warm?: boolean
    model?: string
    dim?: number
    pid?: number
    uptime_s?: number
  } | null
}

export interface EmbedStatus {
  backend: string
  resolution: string
  model: string | null
  dim: number
  warm: boolean
  latency_ms: number | null
  effective_backend: string | null
}

export const daemonApi = {
  status: () => request<DaemonStatus>('/daemon'),
  log: (lines = 200) => request<{ lines: string[]; count: number }>(`/daemon/log?lines=${lines}`),
  start: (port?: number) =>
    request<{ job_id: string }>('/daemon/start', {
      method: 'POST',
      body: JSON.stringify({ port: port ?? null }),
    }),
  stop: () => request<{ job_id: string }>('/daemon/stop', { method: 'POST' }),
  restart: (port?: number) =>
    request<{ job_id: string }>('/daemon/restart', {
      method: 'POST',
      body: JSON.stringify({ port: port ?? null }),
    }),
  autoManage: (enabled: boolean) =>
    request<{ auto_manage_daemon: boolean }>('/daemon/auto-manage', {
      method: 'POST',
      body: JSON.stringify({ enabled }),
    }),
}

export const embedApi = {
  status: () => request<EmbedStatus>('/embed/status'),
}

// ── SPEC-04: Index Management ────────────────────────────────────────────────
export interface IndexStatus {
  files: number
  symbols: number
  chunks: number
  edges: number
  vectors: number
  commits: number
  signals: number
  summaries: number
  last_sync: number
  lag_s: number | null
  fresh: boolean
  embedder: string | null
  fts: boolean
  schema_version: number | null
  admission?: AdmissionReport | null
}

export interface AdmissionReport {
  mode: string
  index_tiers: Record<string, number>
  skipped: Record<string, number>
  examples?: Record<string, string[]>
}

export interface SyncStats {
  files: number
  symbols: number
  chunks: number
  edges: number
  vectors: number
  dirty: number
  deleted: number
  embedded: number
  ms: number
}

export const indexApi = {
  status: () => request<IndexStatus>('/index/status'),
  sync: (full = false, reembed = false) =>
    request<{ job_id: string }>('/index/sync', {
      method: 'POST',
      body: JSON.stringify({ full, reembed }),
    }),
  rebuild: () => request<{ job_id: string }>('/index/rebuild', { method: 'POST' }),
  verify: (repair = false) =>
    request<{ job_id: string }>('/index/verify', {
      method: 'POST',
      body: JSON.stringify({ repair }),
    }),
  vacuum: (days?: number) =>
    request<{ job_id: string }>('/index/vacuum', {
      method: 'POST',
      body: JSON.stringify({ days: days ?? null }),
    }),
  admission: () => request<AdmissionReport>('/admission'),
  explain: (path: string) =>
    request<unknown>(`/admission/explain?path=${encodeURIComponent(path)}`),
}

// ── SPEC-04 §6.2: Filesystem Watch (CORE-16) ──────────────────────────────────
export interface WatchStatus {
  running: boolean
  interval: number
  stopping: boolean
}

export const watchApi = {
  status: () => request<WatchStatus>('/watch/status'),
  start: (interval = 1.0) =>
    request<WatchStatus>(`/watch/start?interval=${interval}`, { method: 'POST' }),
  stop: () => request<WatchStatus>('/watch/stop', { method: 'POST' }),
  // PLAN-05 T5.3: lazy activation — start/stop the watcher when a project
  // becomes/ceases to be the active console project.
  activate: (repo: string, active = true) =>
    request<{ result: string } & WatchStatus>(
      `/watch/activate?repo=${encodeURIComponent(repo)}&active=${active}`,
      { method: 'POST' },
    ),
}

// ── SPEC-04 §6.1: Snapshots (CORE-17) ─────────────────────────────────────────
export interface Snapshot {
  ts: number
  job: string
  health: number | null
  components: Record<string, unknown> | null
  counts: Record<string, number> | null
  severity: Record<string, number> | null
  meta: Record<string, unknown> | null
}

export const snapshotsApi = {
  list: (job?: string, limit = 60) => {
    const params = new URLSearchParams()
    if (job) params.set('job', job)
    params.set('limit', String(limit))
    return request<{ job: string | null; count: number; snapshots: Snapshot[] }>(
      `/snapshots?${params.toString()}`,
    )
  },
}

// ── SPEC-05: Search & Navigation ──────────────────────────────────────────────
export interface SearchResult {
  chunk: string
  path: string
  lines: [number, number]
  symbol: string | null
  score: number
  matched: string[]
  snippet: string
  tier: string
}

export interface SearchEnvelope {
  results: SearchResult[]
  query: string
  count: number
  took_ms: number
  matched_fallback: boolean
  warming: boolean
}

export interface SymbolInfo {
  id: string
  name: string
  kind: string
  path: string
  start_line: number
  end_line: number
  signature: string
  counts: { in: Record<string, number>; out: Record<string, number> }
}

export interface GraphNode {
  id: string
  name?: string
  kind?: string
  path?: string
  start_line?: number
  end_line?: number
  signature?: string
}

export interface GraphEdge {
  src: string
  dst: string
  kind: string
}

export interface GraphPayload {
  root: string
  nodes: GraphNode[]
  edges: GraphEdge[]
}

export interface ContextSection {
  why: string
  meta: Record<string, unknown>
  text: string
}

export interface ContextPack {
  seed: string | null
  budget_tokens: number
  used_tokens: number
  tokens_remaining: number
  budget_utilization: number
  sections: ContextSection[]
  next_ops: string[]
}

export const searchApi = {
  search: (q: string, params: { k?: number; tier?: string; kind?: string } = {}) => {
    const qs = new URLSearchParams({ q })
    if (params.k) qs.set('k', String(params.k))
    if (params.tier) qs.set('tier', params.tier)
    if (params.kind) qs.set('kind', params.kind)
    return request<SearchEnvelope>(`/search?${qs}`)
  },
  symbols: (name: string, limit = 20) =>
    request<{ symbols: SymbolInfo[] }>(`/symbols?name=${encodeURIComponent(name)}&limit=${limit}`),
  graph: (id: string, direction = 'both', depth = 1) =>
    request<GraphPayload>(`/graph?id=${encodeURIComponent(id)}&direction=${direction}&depth=${depth}`),
  context: (params: { query?: string; symbol?: string; budget?: number }) => {
    const qs = new URLSearchParams()
    if (params.query) qs.set('query', params.query)
    if (params.symbol) qs.set('symbol', params.symbol)
    if (params.budget) qs.set('budget', String(params.budget))
    return request<ContextPack>(`/context?${qs}`)
  },
  history: (path: string) =>
    request<{ path: string; commits: string[]; note?: string }>(
      `/history?path=${encodeURIComponent(path)}`,
    ),
}

// ── SPEC-06 Deep File Panel ────────────────────────────────────────────────
export interface FileSymbol {
  id: string
  name: string
  kind: string
  start_line: number
  end_line: number
  signature: string
}

export interface FileChunk {
  id: string
  start_line: number
  end_line: number
  symbol_id: string | null
  tokens: number
}

export interface FileRoute {
  path: string
  kind: string
  methods: string | null
  client: string | null
}

export interface FileFinding {
  id: string
  rule: string
  severity: string
  line: number | null
  title: string
  status: string
}

export interface FileBundle {
  path: string
  found: boolean
  text: string
  symbols: FileSymbol[]
  chunks: FileChunk[]
  routes: FileRoute[]
  findings: FileFinding[]
  vectors_n: number
  vectors_total: number
}

export interface ImpactResult {
  target: string
  risk: string
  seed_files: string[]
  affected_files: string[]
  affected_count: number
  tests_to_run: string[]
  routes_affected: { path: string; kind: string }[]
  open_findings_in_area: number
  hotspot_heat: number
  advice: string[]
  error?: string
}

// ── SPEC-16: Explorer tree (PLAN-07/08 ─────────────────────────────────────
export interface TreeEntry {
  name: string
  path: string
  status?: string
}

export interface TreeListing {
  path: string
  dirs: TreeEntry[]
  files: TreeEntry[]
}

export const fileApi = {
  tree: (path = '') =>
    request<TreeListing>(`/tree?path=${encodeURIComponent(path)}`),
  bundle: (path: string) =>
    request<FileBundle>(`/file?path=${encodeURIComponent(path)}`),
  summary: (path: string) =>
    request<{ path: string; summary?: string; source?: string; error?: string }>(
      `/file/summary?path=${encodeURIComponent(path)}`,
    ),
  impact: (path: string, depth = 2) =>
    request<ImpactResult>(`/file/impact?path=${encodeURIComponent(path)}&depth=${depth}`),
  history: (path: string, n = 8) =>
    request<{ path: string; commits: string[]; note?: string }>(
      `/file/history?path=${encodeURIComponent(path)}&n=${n}`,
    ),
  coverage: (path: string) =>
    request<{ file: string; coverage_pct: number; loaded: unknown[]; note?: string }>(
      `/file/coverage?path=${encodeURIComponent(path)}`,
    ),
  context: (path: string, line?: number) =>
    request<{ suggestions: { type: string; name?: string; count?: number; reason: string }[] }>(
      `/file/context?path=${encodeURIComponent(path)}${line ? `&line=${line}` : ''}`,
    ),
  graph: (path: string) =>
    request<GraphPayload & { seeded: string | null }>(`/file/graph?path=${encodeURIComponent(path)}`),
}

// ── SPEC-07: Quality & Audit ─────────────────────────────────────────────
export type Severity = 'critical' | 'high' | 'medium' | 'low'

export interface HealthReport {
  overall_score: number
  critical_issues: number
  high_priority: number
  test_coverage: { actual_coverage: { coverage_pct: number } } | Record<string, unknown>
  technical_debt: number
  hotspots: { path: string; heat: number; dependents?: number }[]
  recommendations: { priority: string; action: string; impact?: string; effort?: string }[]
}

export interface FindingsSummary {
  open: number
  by_severity: Record<Severity, number>
  critical: number
  high: number
}

export interface QualityFinding {
  id: string
  rule: string
  severity: Severity
  path: string
  line: string
  symbol_id: string | null
  title: string
  detail: string
  suggestion: string
  effort: string
  ts: string
  status: string
}

export interface QuickWin {
  id: string
  rule: string
  severity: Severity
  path: string
  line: string
  title: string
  suggestion: string
  effort: string
}

export interface HealthBreakdown {
  coverage: number
  quality: number
  freshness: number
  complexity: number | null
}

export interface QualityBundle {
  health: HealthReport
  findings: FindingsSummary
  quick_wins: QuickWin[]
  trends: { ts: string; score?: number }[]
  breakdown: HealthBreakdown
  generated_ms: number
}

export interface QualityFindingPage {
  findings: QualityFinding[]
  count: number
  offset: number
  limit: number
}

export const auditApi = {
  bundle: () => request<QualityBundle>('/quality'),
  gaps: () =>
    request<Record<string, unknown>>('/quality/gaps'),
  coverage: () =>
    request<{ coverage_pct?: number; files?: unknown; note?: string }>('/quality/coverage'),
  findings: (params: { severity?: string; rule?: string; path?: string; limit?: number; offset?: number } = {}) => {
    const qs = new URLSearchParams()
    if (params.severity) qs.set('severity', params.severity)
    if (params.rule) qs.set('rule', params.rule)
    if (params.path) qs.set('path', params.path)
    qs.set('limit', String(params.limit ?? 50))
    qs.set('offset', String(params.offset ?? 0))
    return request<QualityFindingPage>(`/quality/findings?${qs}`)
  },
  trends: (metric = 'score') =>
    request<{ metric: string; series: { ts: string; value: number }[] }>(`/quality/trends?metric=${metric}`),
  quickWins: (limit = 10) =>
    request<{ quick_wins: QuickWin[] }>(`/quality/quickwins?limit=${limit}`),
  runAudit: (scopedFile?: string) =>
    request<{ job_id: string; status: string }>('/quality/audit', {
      method: 'POST',
      body: JSON.stringify({ refresh: true, scoped_file: scopedFile ?? null }),
    }),
}

// ── SPEC-08: Memory Lab ─────────────────────────────────────────────────────
export interface MemoryOverview {
  facts_n: number
  episodes_n: number
  patterns_n: number
  profiles: number
  last_consolidation: { ts: number; episodes?: number; patterns?: number; promoted?: number } | null
  daemon_running: boolean
  memory_dir: string
  disk_bytes: number
  last_write: number | null
  initialized: boolean
}

export interface MemoryFact {
  subject: string
  predicate: string
  object_value: unknown
  valid_from: number
  valid_until: number | null
  confidence: number
  source: string
  metadata: Record<string, unknown>
  created_at: number
}

export interface MemoryEpisode {
  id: number
  timestamp: number
  episode_type: string
  context: Record<string, unknown>
  outcome: string | null
  metadata: Record<string, unknown>
  has_embedding: boolean
}

export interface RecallResult {
  type: string
  content: unknown
  timestamp: number
  outcome?: string
}

export const memoryApi = {
  overview: () => request<MemoryOverview>('/memory/overview'),
  facts: (params: { subject?: string; predicate?: string; at?: number; limit?: number } = {}) => {
    const qs = new URLSearchParams()
    if (params.subject) qs.set('subject', params.subject)
    if (params.predicate) qs.set('predicate', params.predicate)
    if (params.at) qs.set('at', String(params.at))
    qs.set('limit', String(params.limit ?? 100))
    return request<{ facts: MemoryFact[] }>(`/memory/facts?${qs}`)
  },
  episodes: (type?: string, limit = 50) => {
    const qs = new URLSearchParams()
    if (type) qs.set('type', type)
    qs.set('limit', String(limit))
    return request<{ episodes: MemoryEpisode[]; count: number }>(`/memory/episodes?${qs}`)
  },
  recall: (query: string) =>
    request<{ query: string; results: RecallResult[]; count: number }>(
      `/memory/recall?query=${encodeURIComponent(query)}`,
    ),
  patterns: (userId = 'default') =>
    request<{ analyzed: Record<string, unknown> | null; learned: MemoryFact[] }>(
      `/memory/patterns?user_id=${userId}`,
    ),
  suggestions: (userId = 'default') =>
    request<{ suggestions: { action: string; reason?: string; confidence?: number; score?: number; source?: string }[] }>(
      `/memory/suggestions?user_id=${userId}`,
    ),
  recordAction: (actionType: string, command?: string, success = true) =>
    request<Record<string, never>>('/memory/action', {
      method: 'POST',
      body: JSON.stringify({ action_type: actionType, command: command ?? null, success }),
    }),
  consolidate: (lookbackDays = 7) =>
    request<{ job_id: string; status: string }>('/memory/consolidate', {
      method: 'POST',
      body: JSON.stringify({ lookback_days: lookbackDays }),
    }),
  clear: (confirm: boolean) =>
    request<{ cleared: boolean }>('/memory/clear', {
      method: 'POST',
      body: JSON.stringify({ confirm }),
    }),
}

// ── SPEC-09: Visualization Suite ─────────────────────────────────────────────
export interface VisOverview {
  health: HealthReport
  findings: FindingsSummary
  quick_wins: QuickWin[]
  trends: { ts: number; score?: number }[]
  breakdown: HealthBreakdown
  gate: { ok: boolean; critical: number; high: number; freshness_hours: number | null }
  languages: { language: string; count: number }[]
  counts: {
    files: number
    symbols: number
    chunks: number
    edges: number
    vectors: number
    vector_coverage_pct: number
  }
}

export interface VisTrend {
  kind: string
  metric: string
  series: { ts: number; value: number }[]
}

export interface VisGit {
  velocity: { week: string; commits: number }[]
  hotspots: {
    path: string
    score: number
    lines: number | null
    size: number | null
    proxy: string
  }[]
  co_change_pairs: { src: string; dst: string }[]
  co_change_total: number
  activity: { ts: number; kind: string; payload: Record<string, unknown> }[]
}

export interface VisFindings {
  by_severity: { severity: string; count: number }[]
  by_rule: { rule: string; count: number }[]
}

export interface RepoMapDir {
  name: string
  files: number
  symbols: number
}

export interface RepoMap {
  directories: RepoMapDir[]
  totals: { files: number; symbols: number }
  hotspots: { path: string; score: number }[]
  navigate?: string
}

export interface VisSignals {
  window_days: number
  signals: { kind: string; path: string; name: string | null; ts: number }[]
  count: number
  kinds: string[]
}

export const vizApi = {
  overview: () => request<VisOverview>('/vis/overview'),
  trends: (kind: string, metric: string, days?: number) =>
    request<VisTrend>(
      `/vis/trends?kind=${encodeURIComponent(kind)}&metric=${encodeURIComponent(metric)}${
        days ? `&days=${days}` : ''
      }`,
    ),
  git: () => request<VisGit>('/vis/git'),
  findings: () => request<VisFindings>('/vis/findings'),
  map: () => request<RepoMap>('/vis/map'),
  signals: (days = 14) => request<VisSignals>(`/vis/signals?days=${days}`),
  graph: (id: string, direction = 'both', depth = 1) =>
    request<GraphPayload & { lod_fallback: boolean; focus: string; direction: string; depth: number }>(
      `/vis/graph?id=${encodeURIComponent(id)}&direction=${direction}&depth=${depth}`,
    ),
}

// ── SPEC-10: Settings & Config (FR-10 write-now) ─────────────────────────────
export type ConfigValueType = 'str' | 'int' | 'float' | 'bool' | 'array'

export interface ConfigKeySchema {
  type: ConfigValueType
  default: unknown
  desc: string
  choices?: string[]
  min?: number
  max?: number
  source: 'default' | 'config.toml' | 'profile'
}

export interface ConfigSchema {
  schema: Record<string, Record<string, ConfigKeySchema>>
  live_schema_version: number | null
  declared_schema_version: number | null
}

export interface ConfigBundle {
  effective: Record<string, Record<string, unknown>>
  file: Record<string, Record<string, unknown>>
  defaults: Record<string, Record<string, unknown>>
  sources: Record<string, Record<string, 'default' | 'config.toml' | 'profile'>>
}

export interface ConfigSaveResult {
  ok: boolean
  written_keys: string[]
  diff: Record<string, { from: unknown; to: unknown }>
  errors?: string[]
}

export interface ConfigValidateResult {
  ok: boolean
  errors: string[]
}

export interface ConfigResetResult {
  ok: boolean
  removed: string[]
}

export interface ConfigReloadResult {
  job_id: string
  status: string
}

export const settingsApi = {
  schema: () => request<ConfigSchema>('/config/schema'),
  bundle: () => request<ConfigBundle>('/config/full'),
  validate: (updates: Record<string, Record<string, unknown>>) =>
    request<ConfigValidateResult>('/config/validate', {
      method: 'POST',
      body: JSON.stringify({ updates }),
    }),
  save: (updates: Record<string, Record<string, unknown>>) =>
    request<ConfigSaveResult>('/config/save', {
      method: 'POST',
      body: JSON.stringify({ updates }),
    }),
  reset: (section: string, keys?: string[]) =>
    request<ConfigResetResult>('/config/reset', {
      method: 'POST',
      body: JSON.stringify({ section, keys: keys ?? null }),
    }),
  reload: () =>
    request<ConfigReloadResult>('/config/reload', {
      method: 'POST',
      body: JSON.stringify({}),
    }),
  env: () => request<{ env: Record<string, string>; live_schema_version: number | null }>('/env'),
}

// ── SPEC-11: Export & Integration ─────────────────────────────────────────────
export type ExportKind = 'repo' | 'findings' | 'index' | 'search'
export type ExportFormat = 'json' | 'markdown'

export interface ExportStatus {
  mcp: { port: number; reachable: boolean }
  daemon: { port: number; reachable: boolean }
  index: { files: number; symbols: number; signals: number; ready: boolean }
  export: { kinds: ExportKind[]; formats: ExportFormat[] }
}

export interface ExportTool {
  name: string
  description: string
  category: string
  params: { name: string; type: string; required: boolean; default?: unknown; help?: string }[]
  returns: string
  invoke: string
}

export interface IngestResult {
  ingested: number
  kind: string
}

export interface VerifyRunResult {
  job_id: string
  status: string
  params: { typecheck: boolean; lint: boolean; audit_check: boolean }
}

export const exportApi = {
  status: () => request<ExportStatus>('/export/status'),
  tools: () => request<{ tools: ExportTool[]; count: number; port: number }>('/export/tools'),
  downloadUrl: (kind: ExportKind, format: ExportFormat, q = '') => {
    const qs = new URLSearchParams({ kind, format })
    if (q) qs.set('q', q)
    return `/api/export?${qs.toString()}`
  },
  ingest: (kind: 'vitest' | 'jest' | 'pytest' | 'tsc' | 'generic', text: string) =>
    request<IngestResult>('/export/ingest', {
      method: 'POST',
      body: JSON.stringify({ kind, text }),
    }),
  verify: (typecheck: boolean, lint: boolean, auditCheck = true) =>
    request<VerifyRunResult>('/verify', {
      method: 'POST',
      body: JSON.stringify({ typecheck, lint, audit_check: auditCheck }),
    }),
}

// ── SPEC-12: Repo Activation (onboarding wizard) ──────────────────────────────
export type OnboardingStatus =
  | 'not_initialized'
  | 'initialized_no_index'
  | 'initialized_stale_index'
  | 'fully_initialized'
  | 'error'

export interface RepoDetection {
  repo_type: string
  languages: string[]
  frameworks: string[]
  has_git: boolean
  git_branch: string | null
  git_uncommitted: number
  file_count: number
}

export interface OnboardingState {
  status: OnboardingStatus
  status_label: string
  cip_dir_exists: boolean
  config_exists: boolean
  index_exists: boolean
  detector_index_fresh: boolean
  git_hooks_installed: boolean
  agents_md_exists: boolean
  indexed: boolean
  fresh: boolean
  needs_onboarding: boolean
  detection: RepoDetection | null
  recommendations: string[]
  error_message: string | null
}

export interface OnboardingResponse extends OnboardingState {
  ok: true
}

export const onboardingApi = {
  status: (path?: string) =>
    request<OnboardingState>(`/onboarding/status${path ? `?path=${encodeURIComponent(path)}` : ''}`),
}

// ── SPEC-19: Projects Registry (multi-project console) ─────────────────────────
export interface ProjectSummary {
  id: string
  root: string
  name: string
  status: string
  last_onboard_ts: number | null
  repo_type: string | null
}

export interface ProjectListResponse {
  projects: ProjectSummary[]
}

export const projectsApi = {
  list: () => request<ProjectListResponse>('/projects'),
  register: (root: string) =>
    request<ProjectSummary>('/projects', {
      method: 'POST',
      body: JSON.stringify({ root }),
    }),
  remove: (id: string) =>
    request<{ id: string; unregistered: boolean }>(`/projects?id=${encodeURIComponent(id)}`, {
      method: 'DELETE',
    }),
  onboard: (id: string) =>
    request<{ job_id: string; status: string; project_id: string }>(
      `/projects/${encodeURIComponent(id)}/onboard`,
      { method: 'POST' },
    ),
  profile: (id: string, profile: Record<string, unknown>) =>
    request<{ ok: boolean }>(`/projects/${encodeURIComponent(id)}/profile`, {
      method: 'POST',
      body: JSON.stringify({ profile }),
    }),
}

// ── SPEC-13: Oracle / Intelligence Surface ────────────────────────────────────
export interface OraclePrediction {
  tool: string
  args: Record<string, unknown>
  confidence: number
  reason: string
}

export interface OracleNext {
  ready: boolean
  predictions: OraclePrediction[]
  reason?: string
  message?: string
}

export interface OracleStory {
  ready: boolean
  story?: { path: string | null; summary: string; source: string; cached: boolean }
  directories?: { name: string; files: number; symbols: number }[]
  totals?: { files: number; symbols: number }
  hotspots?: { path: string; score: number }[]
  reason?: string
  message?: string
}

export interface OracleSummary {
  ready: boolean
  path?: string | null
  summary?: string
  source?: string
  cached?: boolean
  error?: string
  reason?: string
  message?: string
}

export interface OracleSuggestContext {
  ready: boolean
  file?: string
  suggestions?: {
    type: string
    id?: string
    name?: string
    kind?: string
    count?: number
    critical?: number
    reason?: string
  }[]
  reason?: string
  message?: string
}

export const oracleApi = {
  next: (operation: string, symbol = '', query = '') => {
    const qs = new URLSearchParams({ operation })
    if (symbol) qs.set('symbol', symbol)
    if (query) qs.set('query', query)
    return request<OracleNext>(`/oracle/next?${qs.toString()}`)
  },
  repoSummary: () => request<OracleStory>('/oracle/repo-summary'),
  summary: (path: string) =>
    request<OracleSummary>(`/oracle/summary?path=${encodeURIComponent(path)}`),
  suggestContext: (file: string) =>
    request<OracleSuggestContext>(`/oracle/suggest-context?file=${encodeURIComponent(file)}`),
  workflows: () => request<{ workflows: unknown[] }>('/oracle/workflows'),
  workflowRun: (id: string, config?: Record<string, unknown>) =>
    request<{ job_id: string }>(`/oracle/workflows/${id}/run`, {
      method: 'POST',
      body: JSON.stringify({ config: config ?? {} }),
    }),
}
