import { useQuery } from '@tanstack/react-query'
import { lazy, Suspense, useState } from 'react'
import {
  vizApi,
  memoryApi,
  type VisOverview,
  type VisGit,
  type VisFindings,
  type RepoMap,
  type VisSignals,
  type GraphPayload,
} from '@/lib/api'
import {
  RefreshCw, Loader2, HeartPulse, GitBranch, ShieldAlert, Network,
  Activity, Database, Search, Zap,
} from 'lucide-react'
import {
  ResponsiveContainer, LineChart, Line, XAxis, YAxis, Tooltip, CartesianGrid,
  BarChart, Bar, Cell, PieChart, Pie, AreaChart, Area, ScatterChart, Scatter, ZAxis,
} from 'recharts'

// SPEC-09: Visualization Suite — tabbed A–G dashboards over real data.
// Source labels per panel honour the spec §3 (no placeholder art).

type Tab = 'health' | 'growth' | 'git' | 'findings' | 'codegraph' | 'signals' | 'map'

const TABS: { id: Tab; label: string; icon: React.ComponentType<{ className?: string }> }[] = [
  { id: 'health', label: 'Health & Score', icon: HeartPulse },
  { id: 'growth', label: 'Index & Growth', icon: Database },
  { id: 'git', label: 'Git & Activity', icon: GitBranch },
  { id: 'findings', label: 'Quality & Debt', icon: ShieldAlert },
  { id: 'codegraph', label: 'Code Graph', icon: Network },
  { id: 'signals', label: 'Memory & Signals', icon: Activity },
  { id: 'map', label: 'Repo Map', icon: Zap },
]

const GRID = '#27272a'

export function VisualizeView() {
  const [tab, setTab] = useState<Tab>('health')

  return (
    <div className="max-w-6xl mx-auto space-y-5">
      <div className="flex items-end justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-text-primary mb-1">Visualizations</h1>
          <p className="text-text-muted text-sm">Real-data chart suite across health, index, git, quality, code graph, and memory.</p>
        </div>
      </div>

      {/* Group tabs */}
      <div className="flex items-center gap-1 border-b border-border-subtle pb-2 overflow-x-auto">
        {TABS.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            onClick={() => setTab(id)}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors cursor-pointer whitespace-nowrap ${
              tab === id
                ? 'bg-accent/15 text-accent'
                : 'text-text-muted hover:text-text-primary hover:bg-surface-raised'
            }`}
          >
            <Icon className="w-3.5 h-3.5" />
            {label}
          </button>
        ))}
      </div>

      {tab === 'health' && <HealthPanel />}
      {tab === 'growth' && <GrowthPanel />}
      {tab === 'git' && <GitPanel />}
      {tab === 'findings' && <FindingsPanel />}
      {tab === 'codegraph' && <CodeGraphPanel />}
      {tab === 'signals' && <SignalsPanel />}
      {tab === 'map' && <MapPanel />}
    </div>
  )
}

function Panel({
  title,
  source,
  children,
  loading,
  empty,
}: {
  title: string
  source: string
  children: React.ReactNode
  loading?: boolean
  empty?: React.ReactNode
}) {
  return (
    <section className="rounded-lg border border-border bg-surface p-5 space-y-4">
      <div className="flex items-start justify-between gap-3">
        <h2 className="text-sm font-medium text-text-primary">{title}</h2>
        <span className="text-[10px] font-mono text-text-muted bg-surface-raised px-2 py-0.5 rounded border border-border-subtle shrink-0">
          source: {source}
        </span>
      </div>
      {loading ? (
        <p className="flex items-center gap-2 text-xs text-text-muted">
          <Loader2 className="w-3.5 h-3.5 animate-spin text-accent" /> Loading panel…
        </p>
      ) : empty ? (
        <div className="text-xs text-text-muted">{empty}</div>
      ) : (
        children
      )}
    </section>
  )
}

// ── A. Health & Score ─────────────────────────────────────────────────────────
function HealthPanel() {
  const q = useQuery({ queryKey: ['vis-overview'], queryFn: vizApi.overview, refetchInterval: 30_000 })
  const d = q.data
  return (
    <div className="space-y-4">
      <section className="rounded-lg border border-border bg-surface p-5 grid md:grid-cols-4 gap-4">
        <ScoreRing score={d?.health.overall_score} />
        <div className="md:col-span-3 grid grid-cols-2 md:grid-cols-4 gap-3">
          <MiniStat label="Critical" value={d?.findings.critical} tone="error" />
          <MiniStat label="High" value={d?.findings.high} tone="warning" />
          <MiniStat label="Open findings" value={d?.findings.open} />
          <MiniStat
            label="Freshness"
            value={d?.gate.freshness_hours != null ? `${d.gate.freshness_hours}h` : '—'}
          />
        </div>
      </section>

      {d && (
        <Panel title="Health Components (A1/A3)" source="analysis.repo_health_report (+ breakgcdown)" loading={!d}>
          <ComponentBars breakdown={d.breakdown} />
          <div className="flex flex-wrap gap-2 pt-2">
            {Object.entries(d.counts ?? {}).filter(([k]) => k !== 'vector_coverage_pct').map(([k, v]) => (
              <span key={k} className="px-2 py-1 rounded bg-surface-raised border border-border-subtle text-[10px] font-mono text-text-muted">
                {k}: {v}
              </span>
            ))}
            {d.counts?.vector_coverage_pct !== undefined && (
              <span className="px-2 py-1 rounded bg-surface-raised border border-border-subtle text-[10px] font-mono text-accent">
                vector coverage: {d.counts.vector_coverage_pct}%
              </span>
            )}
          </div>
        </Panel>
      )}

      {d && (
        <Panel title="Health Score Trend (A2)" source="events kind='quality' → score">
          <TrendChart kind="quality" metric="score" color="#818cf8" />
        </Panel>
      )}
    </div>
  )
}

function ScoreRing({ score }: { score?: number }) {
  if (score === undefined) {
    return (
      <div className="relative w-28 h-28 flex items-center justify-center rounded-lg border border-border-subtle">
        <Loader2 className="w-4 h-4 animate-spin text-accent" />
      </div>
    )
  }
  const r = 40
  const c = 2 * Math.PI * r
  const filled = (score / 100) * c
  const tone = score >= 80 ? 'text-success' : score >= 60 ? 'text-warning' : 'text-error'
  return (
    <div className="relative w-28 h-28">
      <svg viewBox="0 0 100 100" className="w-28 h-28 -rotate-90">
        <circle cx="50" cy="50" r={r} fill="none" strokeWidth="10" className="stroke-border" />
        <circle
          cx="50" cy="50" r={r} fill="none" strokeWidth="10" strokeLinecap="round"
          strokeDasharray={`${filled} ${c - filled}`} className="stroke-accent"
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className={`text-3xl font-semibold font-mono ${tone}`}>{Math.round(score)}</span>
        <span className="text-[10px] text-text-muted uppercase tracking-wider">Health</span>
      </div>
    </div>
  )
}

function MiniStat({ label, value, tone }: { label: string; value?: number | string; tone?: 'error' | 'warning' }) {
  return (
    <div className="rounded-lg border border-border-subtle bg-surface-raised/40 p-3">
      <p className={`text-xl font-semibold font-mono ${tone === 'error' ? 'text-error' : tone === 'warning' ? 'text-warning' : 'text-text-primary'}`}>
        {value ?? '—'}
      </p>
      <p className="text-[10px] uppercase tracking-wider text-text-muted">{label}</p>
    </div>
  )
}

function ComponentBars({ breakdown }: { breakdown: VisOverview['breakdown'] }) {
  const rows = [
    { label: 'Coverage', value: breakdown.coverage },
    { label: 'Quality', value: breakdown.quality },
    { label: 'Freshness', value: breakdown.freshness },
    ...(breakdown.complexity !== null && breakdown.complexity !== undefined
      ? [{ label: 'Complexity', value: breakdown.complexity }]
      : []),
  ]
  return (
    <div className="space-y-2">
      {rows.map((r) => (
        <div key={r.label} className="flex items-center gap-3">
          <span className="w-24 text-[10px] text-text-muted">{r.label}</span>
          <div className="flex-1 h-2 rounded-full bg-border/60 overflow-hidden">
            <div
              className={`h-full rounded-full ${r.value >= 80 ? 'bg-success' : r.value >= 50 ? 'bg-warning' : 'bg-error'}`}
              style={{ width: `${Math.min(100, r.value)}%` }}
            />
          </div>
          <span className="w-12 text-right text-[10px] font-mono text-text-secondary">{r.value}%</span>
        </div>
      ))}
    </div>
  )
}

// ── B. Index & Growth ─────────────────────────────────────────────────────────
function GrowthPanel() {
  const overview = useQuery({ queryKey: ['vis-overview'], queryFn: vizApi.overview, refetchInterval: 30_000 })
  const stats = overview.data?.counts
  return (
    <div className="space-y-4">
      <section className="rounded-lg border border-border bg-surface p-5 grid grid-cols-2 md:grid-cols-5 gap-3">
        {[
          ['files', stats?.files], ['symbols', stats?.symbols], ['chunks', stats?.chunks],
          ['edges', stats?.edges], ['vectors', stats?.vectors],
        ].map(([k, v]) => (
          <div key={k as string} className="rounded-lg border border-border-subtle bg-surface-raised/40 p-3">
            <p className="text-xl font-semibold font-mono text-text-primary">{v ?? '—'}</p>
            <p className="text-[10px] uppercase tracking-wider text-text-muted">{k}</p>
          </div>
        ))}
      </section>
      <Panel title="Files by Sync (B1)" source="events kind='sync' → files">
        <TrendChart kind="sync" metric="files" color="#34d399" />
      </Panel>
      <Panel title="Index Growth (B1)" source="events kind='sync' → symbols / chunks / edges">
        <IndexGrowthChart />
      </Panel>
      <Panel title="Sync Freshness Timeline (B3)" source="events kind='sync' → ms + ts gaps">
        <TrendChart kind="sync" metric="ms" color="#fbbf24" />
        <span className="block pt-2 text-[10px] text-text-muted font-mono">
          sync intervals drive the freshness gate — last sync within 1h = fresh.
        </span>
      </Panel>
    </div>
  )
}

function IndexGrowthChart() {
  const symbols = useQuery({
    queryKey: ['vis-trend-sync-symbols'],
    queryFn: () => vizApi.trends('sync', 'symbols'),
  })
  const chunks = useQuery({
    queryKey: ['vis-trend-sync-chunks'],
    queryFn: () => vizApi.trends('sync', 'chunks'),
  })
  if (!symbols.data && !chunks.data) {
    return <p className="text-xs text-text-muted">Loading series…</p>
  }
  const sy = symbols.data?.series ?? []
  const ch = chunks.data?.series ?? []
  const merged = sy.map((s, i) => ({
    ts: s.ts,
    symbols: s.value,
    chunks: ch[i]?.value,
  }))
  if (merged.length === 0) {
    return <EmptyTrend kind="sync" />
  }
  return (
    <ResponsiveContainer width="100%" height={220}>
      <AreaChart data={merged}>
        <CartesianGrid stroke={GRID} strokeDasharray="3 3" />
        <XAxis dataKey="ts" tickFormatter={fmtTs} stroke="#71717a" fontSize={10} />
        <YAxis yAxisId="l" stroke="#71717a" fontSize={10} />
        <Tooltip content={<TrendTip />} />
        <Area yAxisId="l" type="monotone" dataKey="symbols" stroke="#a78bfa" fill="#a78bfa22" strokeWidth={2} />
        <Area yAxisId="l" type="monotone" dataKey="chunks" stroke="#60a5fa" fill="#60a5fa22" strokeWidth={2} />
      </AreaChart>
    </ResponsiveContainer>
  )
}

function EmptyTrend({ kind, cta }: { kind: string; cta?: string }) {
  return (
    <div className="text-xs text-text-muted">
      No <span className="font-mono text-accent">{kind}</span> events yet — run a sync/audit to build
      history{cta ? ` (${cta})` : ''}.
    </div>
  )
}

function TrendChart({ kind, metric, color, height = 200 }: { kind: string; metric: string; color?: string; height?: number }) {
  const q = useQuery({
    queryKey: ['vis-trend', kind, metric],
    queryFn: () => vizApi.trends(kind, metric),
  })
  const series = q.data?.series ?? []
  if (q.isLoading) return <p className="text-xs text-text-muted">Loading series…</p>
  if (series.length === 0) return <EmptyTrend kind={kind} />
  return (
    <ResponsiveContainer width="100%" height={height}>
      <LineChart data={series}>
        <CartesianGrid stroke={GRID} strokeDasharray="3 3" />
        <XAxis dataKey="ts" tickFormatter={fmtTs} stroke="#71717a" fontSize={10} />
        <YAxis stroke="#71717a" fontSize={10} />
        <Tooltip content={<TrendTip />} />
        <Line type="monotone" dataKey="value" stroke={color ?? '#818cf8'} strokeWidth={2}
          dot={{ r: 3, fill: color ?? '#818cf8' }} />
      </LineChart>
    </ResponsiveContainer>
  )
}

function fmtTs(ts: number): string {
  if (!ts) return ''
  const d = new Date(ts * 1000)
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getMonth() + 1}/${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

function TrendTip({ active, payload, label }: { active?: boolean; payload?: { value: number; dataKey: string }[]; label?: number }) {
  if (!active || !payload?.length) return null
  return (
    <div className="rounded border border-border bg-surface px-2 py-1.5 text-[10px] font-mono shadow-lg">
      <p className="text-text-muted">{fmtTs(Number(label))}</p>
      {payload.map((p, i) => (
        <p key={i} className="text-text-primary">
          {p.dataKey}: {p.value}
        </p>
      ))}
    </div>
  )
}

// ── C. Git & Activity ─────────────────────────────────────────────────────────
function GitPanel() {
  const q = useQuery({ queryKey: ['vis-git'], queryFn: vizApi.git, refetchInterval: 60_000 })
  const d: VisGit | undefined = q.data
  return (
    <div className="space-y-4">
      <Panel title="Commit Velocity (C1)" source="commits table (12-week)" loading={q.isLoading}
        empty={!d?.velocity?.length ? 'No commits indexed — run git_index to populate the commits table.' : undefined}>
        {!!d?.velocity?.length && (
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={d.velocity}>
              <CartesianGrid stroke={GRID} strokeDasharray="3 3" />
              <XAxis dataKey="week" stroke="#71717a" fontSize={10} />
              <YAxis stroke="#71717a" fontSize={10} allowDecimals={false} />
              <Tooltip content={<TrendTip />} />
              <Bar dataKey="commits" fill="#34d399" radius={[3, 3, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        )}
      </Panel>

      <Panel title="Hotspots (C2)" source="gitindex.hotspots (recency-weighted; size-as-churn proxy · CORE-36)" loading={q.isLoading}
        empty={!d?.hotspots?.length ? 'No hotspot data — happens after git_index populates commit_files.' : undefined}>
        {!!d?.hotspots?.length && (
          <div className="space-y-1.5">
            {d.hotspots.map((h) => (
              <div key={h.path} className="flex items-center gap-3">
                <span className="w-1/2 truncate font-mono text-[10px] text-text-secondary">{h.path}</span>
                <div className="flex-1 h-2 rounded-full bg-border/60 overflow-hidden">
                  <div
                    className={`h-full rounded-full ${h.score >= 3 ? 'bg-error' : h.score >= 1.5 ? 'bg-warning' : 'bg-accent'}`}
                    style={{ width: `${Math.min(100, (h.score / 6) * 100)}%` }}
                  />
                </div>
                <span className="w-8 text-right text-[10px] font-mono text-text-muted">{h.score}</span>
              </div>
            ))}
          </div>
        )}
      </Panel>

      <Panel title="Co-Change Couples (C3)" source="edges kind='co_change' (top 250)" loading={q.isLoading}
        empty={!d?.co_change_total ? 'No co-change edges — run git_index (co_change_min≥2).' : undefined}>
        {!!d?.co_change_total && (
          <div className="flex flex-wrap gap-1.5">
            {d.co_change_pairs.slice(0, 60).map((p, i) => (
              <span key={i} className="px-2 py-0.5 rounded bg-surface-raised border border-border-subtle text-[10px] font-mono text-text-muted">
                {p.src} ⇄ {p.dst}
              </span>
            ))}
            {d.co_change_total > 60 && (
              <span className="px-2 py-0.5 text-[10px] text-text-muted">+{d.co_change_total - 60} more</span>
            )}
          </div>
        )}
      </Panel>

      <Panel title="Activity Feed (C4)" source="events (sync / quality / memory.consolidate)" loading={q.isLoading}
        empty={!d?.activity?.length ? 'No activity yet.' : undefined}>
        {!!d?.activity?.length && (
          <ul className="space-y-1.5">
            {d.activity.slice().reverse().map((a, i) => (
              <li key={i} className="flex items-center gap-3 text-[10px] font-mono">
                <span className="text-text-muted w-11 shrink-0">{fmtTs(a.ts)}</span>
                <span className="px-1.5 py-0.5 rounded bg-surface-raised border border-border-subtle text-accent">{a.kind}</span>
                <span className="text-text-muted truncate">{Object.entries(a.payload).map(([k, v]) => `${k}=${v}`).slice(0, 4).join(' · ')}</span>
              </li>
            ))}
          </ul>
        )}
      </Panel>
    </div>
  )
}

// ── D. Quality & Debt ─────────────────────────────────────────────────────────
function FindingsPanel() {
  const q = useQuery({ queryKey: ['vis-findings'], queryFn: vizApi.findings, refetchInterval: 30_000 })
  const d: VisFindings | undefined = q.data
  const SEV_COLORS: Record<string, string> = {
    critical: '#ef4444', high: '#f59e0b', medium: '#a78bfa', low: '#52525b',
  }
  return (
    <div className="space-y-4">
      <Panel title="Findings by Severity (D1)" source="audit.summarize (open findings)" loading={q.isLoading}
        empty={!d?.by_severity?.length ? <EmptyTrend kind="findings" cta="run audit" /> : undefined}>
        {!!d?.by_severity?.length && (
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={d.by_severity}>
              <CartesianGrid stroke={GRID} strokeDasharray="3 3" />
              <XAxis dataKey="severity" stroke="#71717a" fontSize={10} />
              <YAxis stroke="#71717a" fontSize={10} allowDecimals={false} />
              <Tooltip />
              <Bar dataKey="count" radius={[3, 3, 0, 0]}>
                {d.by_severity.map((s) => (
                  <Cell key={s.severity} fill={SEV_COLORS[s.severity] ?? '#52525b'} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        )}
      </Panel>

      <Panel title="Findings by Rule (D1)" source="findings GROUP BY rule (top 20)" loading={q.isLoading}
        empty={!d?.by_rule?.length ? 'No findings yet — run an audit.' : undefined}>
        {!!d?.by_rule?.length && (
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={d.by_rule} layout="vertical">
              <CartesianGrid stroke={GRID} strokeDasharray="3 3" />
              <XAxis type="number" stroke="#71717a" fontSize={10} allowDecimals={false} />
              <YAxis type="category" dataKey="rule" width={170} stroke="#71717a" fontSize={10} />
              <Tooltip />
              <Bar dataKey="count" fill="#f59e0b" radius={[0, 3, 3, 0]} />
            </BarChart>
          </ResponsiveContainer>
        )}
      </Panel>

      <Panel title="Severity Split" source="findings by_severity → Pie">
        {!!d?.by_severity?.length && (
          <ResponsiveContainer width="100%" height={200}>
            <PieChart>
              <Pie data={d.by_severity} dataKey="count" nameKey="severity" cx="50%" cy="50%" outerRadius={70}
                label={({ name }: { name?: string }) => name ?? ''}>
                {d.by_severity.map((s) => (
                  <Cell key={s.severity} fill={SEV_COLORS[s.severity] ?? '#52525b'} />
                ))}
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
        )}
      </Panel>
    </div>
  )
}

// ── E. Code Graph (3D) ────────────────────────────────────────────────────────
const CodeGraph3D = lazy(() =>
  import('@/components/codegraph/CodeGraph3D').then((m) => ({ default: m.CodeGraph3D })),
)

function CodeGraphPanel() {
  const [query, setQuery] = useState('')
  const [depth, setDepth] = useState(2)
  const [direction, setDirection] = useState<'in' | 'out' | 'both'>('both')
  const [focus, setFocus] = useState<string | null>(null)
  const [graph, setGraph] = useState<(GraphPayload & { lod_fallback?: boolean }) | null>(null)
  const [loading, setLoading] = useState(false)

  const loadGraph = async (id?: string) => {
    setLoading(true)
    try {
      const g = (await vizApi.graph(id ?? focus ?? '', direction, depth)) as GraphPayload & { lod_fallback?: boolean }
      setGraph(g)
      // Merge expansion results without wiping the current view: keep a running
      // node/edge set so click-to-expand pulls in neighbours (E1/E2).
      if (id && id !== (focus ?? '')) {
        setGraph((prev) => {
          if (!prev) return g
          const nodesById = new Map(prev.nodes.map((n) => [n.id, n]))
          g.nodes.forEach((n) => nodesById.set(n.id, n))
          const seen = new Set<string>()
          const edges = [...prev.edges, ...g.edges].filter((e) => {
            if (!nodesById.has(e.src) || !nodesById.has(e.dst)) return false
            const key = `${e.src}|${e.dst}|${e.kind}`
            if (seen.has(key)) return false
            seen.add(key)
            return true
          })
          return { ...g, nodes: [...nodesById.values()], edges, focus: id, depth, direction }
        })
      }
    } finally {
      setLoading(false)
    }
  }

  const seed = async () => {
    // Start from a high-fanout symbol: graph endpoint around a common module.
    setFocus('repo_health_report')
    await loadGraph('repo_health_report')
  }

  return (
    <div className="space-y-4">
      <Panel title="Interactive 3D Code Graph (E1)" source="retrieve.graph + web_bridge.graph payload (caps 200/400)">
        <div className="flex flex-wrap items-center gap-3">
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && focus && loadGraph(focus)}
            placeholder="highlight nodes (enter to re-query)…"
            className="flex-1 min-w-[220px] rounded-lg border border-border bg-bg px-3 py-1.5 text-xs text-text-primary placeholder:text-text-muted focus:outline-none focus:border-accent"
          />
          <input
            value={focus ?? ''}
            onChange={(e) => setFocus(e.target.value)}
            placeholder="symbol id"
            className="flex-1 min-w-[160px] rounded-lg border border-border bg-bg px-3 py-1.5 text-xs font-mono text-text-primary placeholder:text-text-muted focus:outline-none focus:border-accent"
          />
          <button
            onClick={() => focus && loadGraph(focus)}
            disabled={loading || !focus}
            className="flex items-center gap-1.5 rounded-lg border border-border bg-surface px-3 py-1.5 text-xs font-medium text-text-primary hover:border-accent/50 transition-colors cursor-pointer disabled:opacity-50"
          >
            {loading ? <Loader2 className="w-3.5 h-3.5 animate-spin text-accent" /> : <RefreshCw className="w-3.5 h-3.5 text-accent" />}
            Load
          </button>
          <button
            onClick={seed}
            disabled={loading}
            className="rounded-lg border border-border bg-surface px-3 py-1.5 text-xs font-medium text-text-primary hover:border-accent/50 transition-colors cursor-pointer disabled:opacity-50"
          >
            Seed
          </button>
        </div>
        <p className="text-[10px] text-text-muted font-mono">
          seed defaults to <span className="text-accent">repo_health_report</span>; click any node to expand,
          search glows matches, LOD kicks in above 200 nodes / 400 edges.
        </p>
        {graph ? (
          <Suspense fallback={<Loader placeholder="Initializing 3D…" />}>
            <CodeGraph3D
              graph={graph}
              query={query}
              onExpand={(id) => loadGraph(id)}
              depth={depth}
              direction={direction}
              onDepthChange={(d) => setDepth(d)}
              onDirectionChange={(d) => setDirection(d)}
            />
          </Suspense>
        ) : (
          <div className="rounded-lg border border-dashed border-border-subtle h-[420px] flex flex-col items-center justify-center gap-2 text-text-muted">
            <Search className="w-5 h-5" />
            <p className="text-xs">Enter a symbol id and Load, or hit Seed to start from a known module.</p>
          </div>
        )}
      </Panel>
    </div>
  )
}

function Loader({ placeholder }: { placeholder: string }) {
  return (
    <div className="h-[420px] flex items-center justify-center gap-2 text-xs text-text-muted">
      <Loader2 className="w-4 h-4 animate-spin text-accent" /> {placeholder}
    </div>
  )
}

// ── F. Memory & Signals ───────────────────────────────────────────────────────
function SignalsPanel() {
  const signals = useQuery({ queryKey: ['vis-signals'], queryFn: () => vizApi.signals(14), refetchInterval: 30_000 })
  const d: VisSignals | undefined = signals.data
  return (
    <div className="space-y-4">
      <Panel title="Broken Signals (F3)" source="signals table windowed to 14d" loading={signals.isLoading}
        empty={!d?.count ? (
          <span>No signals in the last 14 days — the signals table is populated by
            <span className="font-mono text-accent"> runtime_adapters.broken</span>; currently empty.</span>
        ) : undefined}>
        {!!d?.count && (
          <ul className="space-y-1.5">
            {d.signals.map((s, i) => (
              <li key={i} className="flex items-center gap-3 text-[10px] font-mono">
                <span className="px-1.5 py-0.5 rounded bg-error/15 text-error border border-error/40">{s.kind}</span>
                <span className="text-text-primary">{s.path}</span>
                <span className="text-text-muted">{s.name}</span>
                <span className="ml-auto text-text-muted">{fmtTs(s.ts)}</span>
              </li>
            ))}
          </ul>
        )}
      </Panel>
      <MemoryMiniPanel />
    </div>
  )
}

function MemoryMiniPanel() {
  const facts = useQuery({ queryKey: ['memory-facts'], queryFn: () => memoryApi.facts({ limit: 100 }), refetchInterval: 15_000 })
  const episodes = useQuery({ queryKey: ['memory-episodes'], queryFn: () => memoryApi.episodes(undefined, 100), refetchInterval: 15_000 })
  const factsData = (facts.data?.facts ?? []).map((f) => ({
    ts: f.valid_from,
    confidence: f.confidence,
    subject: f.subject,
  }))
  const episodeData = (episodes.data?.episodes ?? []).map((e) => ({
    ts: e.timestamp,
    outcome: e.outcome,
  }))
  return (
    <Panel title="Memory Timeline (F1/F2)" source="memory.db temporal_facts + episodes.db" loading={facts.isLoading || episodes.isLoading}
      empty={!factsData.length && !episodeData.length ? <EmptyTrend kind="memory" cta="record actions / consolidate" /> : undefined}>
      {!!factsData.length && (
        <ScatterChart width={600} height={140}>
          <CartesianGrid stroke={GRID} strokeDasharray="3 3" />
          <XAxis dataKey="ts" type="number" tickFormatter={fmtTs} stroke="#71717a" fontSize={10} domain={['dataMin', 'dataMax']} />
          <YAxis dataKey="confidence" type="number" stroke="#71717a" fontSize={10} domain={[0, 1]} />
          <ZAxis range={[40, 180]} />
          <Tooltip content={<MemoryTip />} />
          <Scatter data={factsData} fill="#a78bfa" />
        </ScatterChart>
      )}
      {!!episodeData.length && (
        <>
          <p className="text-[10px] text-text-muted mt-2">episodes (colour = outcome)</p>
          <div className="flex flex-wrap gap-1.5">
            {episodeData.map((e, i) => (
              <span
                key={i}
                className={`px-2 py-0.5 rounded text-[10px] font-mono border ${
                  e.outcome === 'success' ? 'bg-success/15 text-success border-success/40'
                    : e.outcome === 'failure' ? 'bg-error/15 text-error border-error/40'
                      : 'bg-surface-raised text-text-muted border-border-subtle'
                }`}
              >
                {e.outcome ?? 'unknown'}
              </span>
            ))}
          </div>
        </>
      )}
    </Panel>
  )
}

function MemoryTip({ active, payload }: { active?: boolean; payload?: { payload: { subject?: string; confidence?: number; outcome?: string } }[] }) {
  if (!active || !payload?.length) return null
  const p = payload[0].payload
  return (
    <div className="rounded border border-border bg-surface px-2 py-1.5 text-[10px] font-mono shadow-lg">
      <p className="text-text-primary">{p.subject ?? p.outcome ?? ''}</p>
      {p.confidence !== undefined && <p className="text-text-muted">confidence {Math.round(p.confidence * 100)}%</p>}
    </div>
  )
}

// ── G. Repo Map ───────────────────────────────────────────────────────────────
function MapPanel() {
  const q = useQuery({ queryKey: ['vis-map'], queryFn: vizApi.map, refetchInterval: 60_000 })
  const d: RepoMap | undefined = q.data
  const maxFiles = Math.max(1, ...(d?.directories ?? []).map((x) => x.files))
  return (
    <div className="space-y-4">
      <Panel title="Repository Tree-Map (G1)" source="summarize.map_ + files per directory" loading={q.isLoading}
        empty={!d?.directories?.length ? 'No directories indexed yet.' : undefined}>
        {!!d?.directories?.length && (
          <div className="flex flex-wrap items-stretch gap-2">
            {d.directories.map((dir) => {
              const heat = dir.files / maxFiles
              return (
                <div
                  key={dir.name}
                  className="rounded-lg border border-border-subtle bg-surface-raised/40 p-3 min-w-[150px] flex-1"
                  style={{ borderLeftColor: `rgba(167,139,250,${0.2 + heat * 0.8})`, borderLeftWidth: 3 }}
                >
                  <p className="text-sm font-mono text-text-primary truncate">{dir.name}</p>
                  <p className="text-[11px] text-text-muted">files: {dir.files}</p>
                  <p className="text-[11px] text-text-muted">symbols: {dir.symbols}</p>
                </div>
              )
            })}
          </div>
        )}
        {d?.totals && (
          <p className="text-[11px] text-text-muted font-mono pt-1">
            totals → files: {d.totals.files} · symbols: {d.totals.symbols}
          </p>
        )}
      </Panel>
      <Panel title="Repo Hotspots (G2)" source="gitindex.hotspots (top 5)" loading={q.isLoading}
        empty={!d?.hotspots?.length ? 'No hotspots yet.' : undefined}>
        {!!d?.hotspots?.length && (
          <ul className="space-y-1.5">
            {d.hotspots.map((h) => (
              <li key={h.path} className="flex items-center gap-3 text-[10px] font-mono">
                <span className="px-1.5 py-0.5 rounded bg-warning/15 text-warning border border-warning/40">{h.score}</span>
                <span className="text-text-primary truncate">{h.path}</span>
              </li>
            ))}
          </ul>
        )}
      </Panel>
      {d ? (
        <p className="text-[10px] font-mono text-text-muted">navigate: {d.navigate}</p>
      ) : null}
    </div>
  )
}