import { Suspense, lazy } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useSearchParams } from 'react-router-dom'
import { fileApi, type FileBundle, type ImpactResult } from '@/lib/api'
import {
  FileCode, Loader2, AlertTriangle, GitCommit, Target, Sparkles,
  ShieldCheck, Network, History, Package, ChevronRight,
} from 'lucide-react'

const FileEditor = lazy(() => import('@/components/file/FileEditor'))

const severityColor: Record<string, string> = {
  critical: 'bg-red-500/15 text-red-400',
  high: 'bg-orange-500/15 text-orange-400',
  medium: 'bg-warning/15 text-warning',
  low: 'bg-sky-500/15 text-sky-400',
}

export function FileView() {
  const [params] = useSearchParams()
  const path = params.get('path') ?? ''

  const bundle = useQuery({
    queryKey: ['file', path],
    queryFn: () => fileApi.bundle(path),
    enabled: !!path,
  })

  if (!path) {
    return (
      <div className="flex-1 flex items-center justify-center text-text-muted text-sm">
        Open a file from search results to see its intelligence panel.
      </div>
    )
  }

  return (
    <div className="flex h-full gap-3">
      {/* Left: read-only Monaco */}
      <div className="flex-1 min-w-0 rounded-lg border border-border bg-surface overflow-hidden flex flex-col">
        <div className="flex items-center gap-2 px-3 py-2 border-b border-border-subtle shrink-0">
          <FileCode className="w-4 h-4 text-accent shrink-0" />
          <span className="font-mono text-xs text-text-primary truncate">{path}</span>
          {bundle.isLoading && <Loader2 className="w-3.5 h-3.5 animate-spin text-text-muted ml-auto" />}
          {bundle.data && (
            <span className="ml-auto text-[10px] text-text-muted font-mono shrink-0">
              {bundle.data.text.split('\n').length} lines · {bundle.data.symbols.length} symbols ·{' '}
              {bundle.data.vectors_n}/{bundle.data.vectors_total} embedded
            </span>
          )}
        </div>
        <div className="flex-1 min-h-0">
          {bundle.data ? (
            <Suspense
              fallback={
                <div className="h-full flex items-center justify-center gap-2 text-text-muted text-sm p-8">
                  <Loader2 className="w-4 h-4 animate-spin" /> loading editor…
                </div>
              }
            >
              <FileEditor text={bundle.data.text} path={path} />
            </Suspense>
          ) : (
            <div className="h-full flex items-center justify-center text-text-muted text-sm">
              <Loader2 className="w-4 h-4 animate-spin mr-2" /> loading file…
            </div>
          )}
        </div>
      </div>

      {/* Right: intelligence rail */}
      <div className="w-80 shrink-0 overflow-y-auto space-y-3 pr-1">
        <SummarySection path={path} />
        <SymbolsSection bundle={bundle.data} />
        <RelationsSection path={path} />
        <ImpactSection path={path} />
        <FindingsSection bundle={bundle.data} />
        <HistorySection path={path} />
        <CoverageSection path={path} />
        <EditContextSection path={path} />
      </div>
    </div>
  )
}

// ── Rail sections (lazy per-section data; empty = explicit none state) ───────

function SectionShell({ icon, title, children, loading }: {
  icon: React.ReactNode; title: string; children: React.ReactNode; loading?: boolean
}) {
  return (
    <section className="rounded-lg border border-border bg-surface p-3">
      <div className="flex items-center gap-1.5 mb-2">
        {icon}
        <h3 className="text-[11px] font-medium text-text-primary uppercase tracking-wide">{title}</h3>
        {loading && <Loader2 className="w-3 h-3 animate-spin text-text-muted ml-auto" />}
      </div>
      {children}
    </section>
  )
}

function SummarySection({ path }: { path: string }) {
  const q = useQuery({ queryKey: ['file-summary', path], queryFn: () => fileApi.summary(path) })
  const d = q.data
  return (
    <SectionShell icon={<Sparkles className="w-3.5 h-3.5 text-accent" />} title="Summary" loading={q.isLoading}>
      {q.isLoading ? (
        <p className="text-xs text-text-muted">…</p>
      ) : d?.summary ? (
        <div>
          <p className="text-xs text-text-secondary whitespace-pre-wrap leading-relaxed">{d.summary}</p>
          <span className="inline-block mt-1.5 text-[10px] px-1.5 py-0.5 rounded bg-surface-raised text-text-muted font-mono">
            {d.source}
          </span>
        </div>
      ) : (
        <p className="text-xs text-text-muted">No summary yet. Run index sync to populate.</p>
      )}
    </SectionShell>
  )
}

function SymbolsSection({ bundle }: { bundle?: FileBundle }) {
  if (!bundle) return null
  const symbols = bundle.symbols
  return (
    <SectionShell icon={<Target className="w-3.5 h-3.5 text-accent" />} title={`Symbols (${symbols.length})`}>
      {symbols.length === 0 ? (
        <p className="text-xs text-text-muted">No symbols indexed in this file.</p>
      ) : (
        <ul className="space-y-1 max-h-56 overflow-y-auto">
          {symbols.map((s) => (
            <li key={s.id} className="flex items-center gap-2 text-xs">
              <span className="text-[10px] px-1.5 py-0.5 rounded bg-surface-raised text-text-muted font-mono shrink-0 w-16 text-center">
                {s.kind}
              </span>
              <span className="font-mono text-text-primary truncate" title={s.signature || s.name}>{s.name}</span>
              <span className="ml-auto text-[10px] text-text-muted shrink-0">{s.start_line}</span>
            </li>
          ))}
        </ul>
      )}
    </SectionShell>
  )
}

function RelationsSection({ path }: { path: string }) {
  const q = useQuery({ queryKey: ['file-graph', path], queryFn: () => fileApi.graph(path) })
  const d = q.data
  return (
    <SectionShell icon={<Network className="w-3.5 h-3.5 text-accent" />} title="Relations" loading={q.isLoading}>
      {q.isLoading ? (
        <p className="text-xs text-text-muted">…</p>
      ) : d && d.nodes.length > 0 ? (
        <div>
          <p className="text-xs text-text-secondary">
            {d.nodes.length} nodes · {d.edges.length} edges seeded by{' '}
            <span className="font-mono text-accent">{d.seeded}</span>
          </p>
        </div>
      ) : (
        <p className="text-xs text-text-muted">No relationships found. Re-sync to refresh edges.</p>
      )}
    </SectionShell>
  )
}

function ImpactSection({ path }: { path: string }) {
  const q = useQuery({ queryKey: ['file-impact', path], queryFn: () => fileApi.impact(path) })
  const d: ImpactResult | undefined = q.data
  const riskColor = d?.risk === 'high' ? 'text-red-400' : d?.risk === 'medium' ? 'text-warning' : 'text-success'
  return (
    <SectionShell icon={<ShieldCheck className="w-3.5 h-3.5 text-accent" />} title="Impact" loading={q.isLoading}>
      {q.isLoading ? (
        <p className="text-xs text-text-muted">…</p>
      ) : d?.error ? (
        <p className="text-xs text-text-muted">{d.error}</p>
      ) : d ? (
        <div className="space-y-2">
          <div className="flex items-center gap-2">
            <span className={`text-sm font-semibold capitalize ${riskColor}`}>{d.risk} risk</span>
            <span className="ml-auto text-[10px] text-text-muted font-mono">{d.affected_count} files</span>
          </div>
          <div className="flex flex-wrap gap-1">
            {d.tests_to_run.length > 0 ? (
              <span className="text-[10px] px-1.5 py-0.5 rounded bg-success/15 text-success font-mono">
                {d.tests_to_run.length} tests
              </span>
            ) : (
              <span className="text-[10px] px-1.5 py-0.5 rounded bg-surface-raised text-text-muted font-mono">
                no tests cover this
              </span>
            )}
            {d.routes_affected.length > 0 && (
              <span className="text-[10px] px-1.5 py-0.5 rounded bg-accent/15 text-accent font-mono">
                {d.routes_affected.length} routes
              </span>
            )}
            {d.open_findings_in_area > 0 && (
              <span className="text-[10px] px-1.5 py-0.5 rounded bg-red-500/15 text-red-400 font-mono">
                {d.open_findings_in_area} findings
              </span>
            )}
          </div>
          {d.hotspot_heat > 0 && (
            <p className="text-[10px] text-text-muted">hotspot heat {d.hotspot_heat}</p>
          )}
          {d.advice.length > 0 && (
            <ul className="space-y-1 mt-1">
              {d.advice.slice(0, 3).map((a, i) => (
                <li key={i} className="text-[11px] text-text-secondary flex gap-1.5">
                  <ChevronRight className="w-3 h-3 text-text-muted shrink-0 mt-0.5" /> {a}
                </li>
              ))}
            </ul>
          )}
        </div>
      ) : null}
    </SectionShell>
  )
}

function FindingsSection({ bundle }: { bundle?: FileBundle }) {
  if (!bundle) return null
  const findings = bundle.findings
  return (
    <SectionShell
      icon={<AlertTriangle className="w-3.5 h-3.5 text-warning" />}
      title={`Findings (${findings.length})`}
    >
      {findings.length === 0 ? (
        <p className="text-xs text-text-muted">No findings — good.</p>
      ) : (
        <ul className="space-y-1.5 max-h-60 overflow-y-auto">
          {findings.map((f) => (
            <li key={f.id} className="text-xs">
              <span className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded ${severityColor[f.severity] ?? 'bg-surface-raised text-text-muted'}`}>
                {f.severity}
              </span>
              <p className="mt-1 text-text-secondary">{f.title}</p>
              <p className="text-[10px] text-text-muted font-mono">{f.rule}{f.line ? `:${f.line}` : ''}</p>
            </li>
          ))}
        </ul>
      )}
    </SectionShell>
  )
}

function HistorySection({ path }: { path: string }) {
  const q = useQuery({ queryKey: ['file-history', path], queryFn: () => fileApi.history(path) })
  const commits = q.data?.commits ?? []
  return (
    <SectionShell icon={<History className="w-3.5 h-3.5 text-accent" />} title="History" loading={q.isLoading}>
      {q.isLoading ? (
        <p className="text-xs text-text-muted">…</p>
      ) : commits.length === 0 ? (
        <p className="text-xs text-text-muted">No commits for this file.</p>
      ) : (
        <ul className="space-y-1 max-h-44 overflow-y-auto font-mono text-[11px] text-text-secondary">
          {commits.map((c, i) => (
            <li key={i} className="truncate">• {c}</li>
          ))}
        </ul>
      )}
    </SectionShell>
  )
}

function CoverageSection({ path }: { path: string }) {
  const q = useQuery({ queryKey: ['file-coverage', path], queryFn: () => fileApi.coverage(path) })
  const d = q.data
  return (
    <SectionShell icon={<Package className="w-3.5 h-3.5 text-accent" />} title="Coverage & gaps" loading={q.isLoading}>
      {q.isLoading ? (
        <p className="text-xs text-text-muted">…</p>
      ) : d ? (
        <div>
          <p className="text-xs text-text-secondary">
            Repo coverage: <span className="text-text-primary font-medium">{d.coverage_pct}%</span>
          </p>
          <p className="text-[10px] text-text-muted mt-1">{d.note}</p>
        </div>
      ) : null}
    </SectionShell>
  )
}

function EditContextSection({ path }: { path: string }) {
  const q = useQuery({ queryKey: ['file-editctx', path], queryFn: () => fileApi.context(path) })
  const d = q.data
  return (
    <SectionShell icon={<GitCommit className="w-3.5 h-3.5 text-accent" />} title="Edit context" loading={q.isLoading}>
      {q.isLoading ? (
        <p className="text-xs text-text-muted">…</p>
      ) : d && d.suggestions.length > 0 ? (
        <ul className="space-y-1 max-h-56 overflow-y-auto">
          {d.suggestions.map((s, i) => (
            <li key={i} className="text-xs text-text-secondary flex gap-1.5">
              <span className="text-[10px] px-1 py-0.5 rounded bg-surface-raised text-text-muted font-mono shrink-0 capitalize">
                {s.type}
              </span>
              <span className="truncate">{s.name ?? `${s.count ?? ''}${s.count ? ' ' : ''}${s.reason}`}</span>
            </li>
          ))}
        </ul>
      ) : (
        <p className="text-xs text-text-muted">No edit-context suggestions.</p>
      )}
    </SectionShell>
  )
}