import { useQuery } from '@tanstack/react-query'
import { useCallback, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  BookOpenText, Braces, FileText, GitCommitHorizontal, Info, Loader2,
  Lightbulb, RefreshCw, Sparkles, Target, Wrench, TriangleAlert, Zap,
} from 'lucide-react'
import { oracleApi, type OracleStory, type OraclePrediction } from '@/lib/api'

const OPS = [
  { op: 'symbol', label: 'Symbol lookup' },
  { op: 'impact', label: 'Impact analysis' },
  { op: 'search', label: 'Search' },
  { op: 'graph', label: 'Graph' },
  { op: 'broken', label: 'Broken tests' },
]

const TOOL_ICON: Record<string, typeof Zap> = {
  graph: GitCommitHorizontal,
  context: Braces,
  search: FileText,
  broken: TriangleAlert,
  coverage: Target,
  findings: Wrench,
  refactors: Wrench,
}

const TOOL_LABEL: Record<string, string> = {
  graph: 'Open graph',
  context: 'Build context',
  search: 'Search',
  broken: 'Broken tests',
  coverage: 'Coverage',
  findings: 'Findings',
  refactors: 'Refactors',
}

type CardProps = {
  title: string
  icon: React.ReactNode
  children: React.ReactNode
  aside?: React.ReactNode
}

function Card({ title, icon, children, aside }: CardProps) {
  return (
    <div className="rounded-xl border border-border bg-surface p-4">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          {icon}
          <h2 className="text-sm font-medium text-text-primary">{title}</h2>
        </div>
        {aside}
      </div>
      {children}
    </div>
  )
}

function SourceBadge({ source }: { source?: string }) {
  if (!source) return null
  const llm = source.startsWith('llm')
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-medium ${
        llm ? 'bg-accent/15 text-accent-hover' : 'bg-border/40 text-text-muted'
      }`}
    >
      <Sparkles className="w-3 h-3" />
      {llm ? 'LLM' : 'Structural'}
    </span>
  )
}

function NotReady({ message }: { message?: string }) {
  return (
    <div className="flex items-start gap-2 rounded-lg border border-warning/30 bg-warning/5 px-3 py-2.5 text-sm text-text-secondary">
      <Info className="w-4 h-4 shrink-0 mt-0.5 text-warning" />
      <span>{message ?? 'Run a sync first — no index found yet.'}</span>
    </div>
  )
}

function Loading() {
  return (
    <div className="flex items-center justify-center py-16">
      <Loader2 className="w-6 h-6 animate-spin text-accent" />
    </div>
  )
}

function RepoStoryCard({ data }: { data: OracleStory | undefined }) {
  if (!data) return <Loading />
  if (!data.ready) return <NotReady message={data.message} />
  const story = data.story?.summary ?? ''
  return (
    <Card
      title="About this repo"
      icon={<BookOpenText className="w-4 h-4 text-accent" />}
      aside={<SourceBadge source={data.story?.source} />}
    >
      <pre className="whitespace-pre-wrap font-mono text-xs text-text-secondary leading-relaxed">{story}</pre>
      <div className="mt-3 grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs">
        <div className="rounded-lg border border-border-subtle bg-surface-raised/40 px-3 py-2">
          <div className="text-text-muted mb-1">Top-level dirs</div>
          <div className="flex flex-wrap gap-1.5">
            {(data.directories ?? []).map((d) => (
              <span key={d.name} className="rounded bg-border/30 px-1.5 py-0.5 text-text-secondary">
                {d.name} <span className="text-text-muted">· {d.files}</span>
              </span>
            ))}
          </div>
        </div>
        <div className="rounded-lg border border-border-subtle bg-surface-raised/40 px-3 py-2">
          <div className="text-text-muted mb-1">Hotspots</div>
          {(data.hotspots ?? []).length === 0 ? (
            <div className="text-text-muted">none</div>
          ) : (
            <div className="space-y-0.5">
              {(data.hotspots ?? []).map((h) => (
                <div key={h.path} className="flex justify-between gap-2 text-text-secondary">
                  <span className="truncate font-mono">{h.path}</span>
                  <span className="text-text-muted shrink-0">{h.score}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </Card>
  )
}

function SummaryCard({ path, onPath }: { path: string; onPath: (p: string) => void }) {
  const [local, setLocal] = useState(path)
  const q = useQuery({
    queryKey: ['oracle-summary', path],
    queryFn: () => oracleApi.summary(path),
    enabled: path.length > 0,
  })
  const submit = useCallback(() => onPath(local.trim().replace(/^\/+/, '')), [local, onPath])

  return (
    <Card
      title="File / directory summary"
      icon={<FileText className="w-4 h-4 text-accent" />}
      aside={
        q.data?.ready ? (
          <SourceBadge source={q.data.source} />
        ) : (
          <button
            onClick={() => q.refetch()}
            className="inline-flex items-center gap-1 rounded px-2 py-0.5 text-[11px] text-text-muted hover:text-text-primary"
          >
            <RefreshCw className="w-3 h-3" /> Re-run
          </button>
        )
      }
    >
      <div className="flex gap-2">
        <input
          value={local}
          onChange={(e) => setLocal(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && submit()}
          placeholder="e.g. lib/cipkg/summarize.py"
          className="flex-1 rounded-lg border border-border bg-surface-raised/60 px-3 py-2 font-mono text-sm text-text-primary outline-none focus:border-accent"
        />
        <button
          onClick={submit}
          className="rounded-lg bg-accent px-3 py-2 text-sm font-medium text-white hover:bg-accent-hover"
        >
          Summarize
        </button>
      </div>
      {q.isLoading ? (
        <Loading />
      ) : q.isError ? (
        <div className="text-sm text-error mt-3">Failed: {String(q.error)}</div>
      ) : q.data && !q.data.ready ? (
        <div className="mt-3">
          <NotReady message={q.data.message} />
        </div>
      ) : q.data?.error ? (
        <div className="mt-3 text-sm text-warning">Not indexed: {q.data.error}</div>
      ) : q.data?.summary ? (
        <pre className="mt-3 whitespace-pre-wrap font-mono text-xs text-text-secondary leading-relaxed">
          {q.data.summary}
        </pre>
      ) : null}
    </Card>
  )
}

function SuggestContextCard() {
  const [file, setFile] = useState('')
  const [open, setOpen] = useState<string | null>(null)
  const q = useQuery({
    queryKey: ['oracle-suggest', file],
    queryFn: () => oracleApi.suggestContext(file),
    enabled: file.length > 0,
  })

  return (
    <Card
      title="Edit context"
      icon={<Target className="w-4 h-4 text-accent" />}
      aside={
        q.data?.ready ? (
          <button
            onClick={() => q.refetch()}
            className="inline-flex items-center gap-1 rounded px-2 py-0.5 text-[11px] text-text-muted hover:text-text-primary"
          >
            <RefreshCw className="w-3 h-3" /> Re-run
          </button>
        ) : null
      }
    >
      <input
        value={file}
        onChange={(e) => setFile(e.target.value)}
        placeholder="File about to be edited — e.g. lib/cipkg/summarize.py"
        className="w-full rounded-lg border border-border bg-surface-raised/60 px-3 py-2 font-mono text-sm text-text-primary outline-none focus:border-accent"
      />
      {q.isLoading ? (
        <Loading />
      ) : q.isError ? (
        <div className="text-sm text-error mt-3">Failed: {String(q.error)}</div>
      ) : q.data && !q.data.ready ? (
        <div className="mt-3">
          <NotReady message={q.data.message} />
        </div>
      ) : q.data?.suggestions && q.data.suggestions.length === 0 ? (
        <div className="mt-3 text-sm text-text-muted">No context suggestions for this file.</div>
      ) : (
        q.data?.suggestions && (
          <div className="mt-3 space-y-1.5">
            {q.data.suggestions.map((s, i) => {
              const detail =
                s.type === 'impact'
                  ? `${s.count} file${s.count === 1 ? '' : 's'} import this file`
                  : s.type === 'findings'
                    ? `${s.critical && s.critical > 0 ? `${s.critical} critical · ` : ''}${s.count} finding${s.count === 1 ? '' : 's'}`
                    : s.name ?? s.reason
              const tone =
                s.type === 'warning' ? 'text-warning' : s.type === 'findings' ? 'text-accent-hover' : 'text-text-secondary'
              return (
                <div key={i} className="rounded-lg border border-border-subtle bg-surface-raised/30 px-3 py-2 text-sm">
                  <button
                    onClick={() => setOpen(open === `${i}` ? null : `${i}`)}
                    className="w-full flex items-center justify-between gap-2 text-left"
                  >
                    <span className="font-medium text-text-primary capitalize">{s.type}</span>
                    <span className={`text-xs ${tone}`}>{detail}</span>
                  </button>
                  {open === `${i}` && (
                    <div className="mt-1.5 text-xs text-text-muted leading-relaxed">
                      <div className="font-mono">{s.id ?? ''}</div>
                      <div>{s.reason}</div>
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        )
      )}
    </Card>
  )
}

function NextContextCard({ operation, onOperation }: { operation: string; onOperation: (op: string) => void }) {
  const navigate = useNavigate()
  const [symbol, setSymbol] = useState('')
  const q = useQuery({
    queryKey: ['oracle-next', operation, symbol],
    queryFn: () => oracleApi.next(operation, symbol),
    enabled: operation.length > 0,
  })

  const navigatePrediction = (p: OraclePrediction) => {
    const a = p.args ?? {}
    switch (p.tool) {
      case 'search':
        navigate(`/search?q=${encodeURIComponent(String(a.query ?? ''))}`)
        break
      case 'graph':
      case 'symbol':
        navigate(`/search?mode=symbols&q=${encodeURIComponent(String(a.name ?? a.id ?? ''))}`)
        break
      case 'coverage':
      case 'findings':
      case 'refactors':
        navigate('/quality')
        break
      case 'broken':
        navigate('/export')
        break
      default:
        navigate('/search')
    }
  }

  return (
    <Card
      title="What should I do next?"
      icon={<Lightbulb className="w-4 h-4 text-warning" />}
      aside={
        <div className="flex items-center gap-1">
          <select
            value={operation}
            onChange={(e) => onOperation(e.target.value)}
            className="rounded-lg border border-border bg-surface-raised/60 px-2 py-1 text-xs text-text-secondary outline-none focus:border-accent"
          >
            <option value="">pick an operation…</option>
            {OPS.map((o) => (
              <option key={o.op} value={o.op}>{o.label}</option>
            ))}
          </select>
          <button
            onClick={() => q.refetch()}
            className="rounded p-1 text-text-muted hover:text-text-primary"
            aria-label="Re-run predictions"
          >
            <RefreshCw className="w-3.5 h-3.5" />
          </button>
        </div>
      }
    >
      {operation && (operation === 'symbol' || operation === 'graph') && (
        <input
          value={symbol}
          onChange={(e) => setSymbol(e.target.value)}
          placeholder="Symbol id — e.g. python://lib/cipkg/summarize.py/#summary"
          className="w-full rounded-lg border border-border bg-surface-raised/60 px-3 py-2 font-mono text-xs text-text-primary outline-none focus:border-accent"
        />
      )}
      {q.isLoading ? (
        <div className="mt-3">
          <Loading />
        </div>
      ) : q.isError ? (
        <div className="text-sm text-error mt-3">Failed: {String(q.error)}</div>
      ) : (
        q.data?.predictions && (
          <div className="mt-3 grid grid-cols-1 sm:grid-cols-3 gap-2">
            {q.data.predictions.map((p, i) => {
              const Icon = TOOL_ICON[p.tool] ?? Zap
              return (
                <button
                  key={i}
                  onClick={() => navigatePrediction(p)}
                  className="rounded-lg border border-border-subtle bg-surface-raised/30 px-3 py-2 text-left cursor-pointer hover:border-accent/50 hover:bg-surface-raised/50 transition-colors"
                >
                  <div className="flex items-center gap-1.5 mb-1">
                    <Icon className="w-3.5 h-3.5 text-accent" />
                    <span className="text-sm font-medium text-text-primary">{TOOL_LABEL[p.tool] ?? p.tool}</span>
                  </div>
                  <div className="text-xs text-text-secondary leading-snug min-h-[2.5em]">{p.reason}</div>
                  <div className="mt-1.5 text-[11px] text-text-muted">
                    confidence <span className="text-text-secondary">~{Math.round(p.confidence * 100)}%</span> (estimated)
                  </div>
                </button>
              )
            })}
          </div>
        )
      )}
    </Card>
  )
}

export function OracleView() {
  const repoQ = useQuery({ queryKey: ['oracle-repo'], queryFn: oracleApi.repoSummary })
  const [path, setPath] = useState('lib/cipkg/summarize.py')
  const [operation, setOperation] = useState('symbol')

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-text-primary mb-1">Oracle / Intelligence</h1>
        <p className="text-text-muted text-sm">
          Repo story, file summaries, edit context, and predictive next-context. All structural/offline
          unless an LLM backend is configured — nothing here ever loads an embedding model.
        </p>
      </div>

      <RepoStoryCard data={repoQ.data} />

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <SummaryCard key={path} path={path} onPath={setPath} />
        <SuggestContextCard />
      </div>

      <NextContextCard operation={operation} onOperation={setOperation} />
    </div>
  )
}