import { useQuery, useQueryClient } from '@tanstack/react-query'
import {
  memoryApi,
  type MemoryFact,
  type MemoryEpisode,
  type RecallResult,
} from '@/lib/api'
import { useState } from 'react'
import {
  Loader2, Database, Brain, Layers, User, Search, Zap,
  Trash2, Clock, Circle,
} from 'lucide-react'

type Tab = 'facts' | 'episodes' | 'patterns' | 'profile' | 'recall'

const TABS: { id: Tab; label: string; icon: React.ComponentType<{ className?: string }> }[] = [
  { id: 'facts', label: 'Temporal Graph', icon: Brain },
  { id: 'episodes', label: 'Episodes', icon: Clock },
  { id: 'patterns', label: 'Patterns', icon: Layers },
  { id: 'profile', label: 'Learning Profile', icon: User },
  { id: 'recall', label: 'Recall', icon: Search },
]

export function MemoryView() {
  const [tab, setTab] = useState<Tab>('facts')
  const [action, setAction] = useState<string | null>(null)
  const [confirmClear, setConfirmClear] = useState(false)
  const qc = useQueryClient()

  const overview = useQuery({
    queryKey: ['memory-overview'],
    queryFn: memoryApi.overview,
    refetchInterval: 10_000,
  })

  const facts = useQuery({
    queryKey: ['memory-facts'],
    queryFn: () => memoryApi.facts({ limit: 200 }),
    enabled: tab === 'facts',
  })
  const episodes = useQuery({
    queryKey: ['memory-episodes'],
    queryFn: () => memoryApi.episodes(undefined, 100),
    enabled: tab === 'episodes',
  })
  const patterns = useQuery({
    queryKey: ['memory-patterns'],
    queryFn: () => memoryApi.patterns(),
    enabled: tab === 'patterns',
  })
  const suggestions = useQuery({
    queryKey: ['memory-suggestions'],
    queryFn: () => memoryApi.suggestions(),
    enabled: tab === 'profile',
  })
  const recall = useQuery({
    queryKey: ['memory-recall'],
    queryFn: () => memoryApi.recall(''),
    enabled: tab === 'recall',
  })

  const d = overview.data

  const runConsolidate = async () => {
    setAction('consolidate')
    try {
      await memoryApi.consolidate(7)
      await Promise.allSettled([overview.refetch(), facts.refetch(), patterns.refetch()])
    } finally {
      setAction(null)
    }
  }

  const clearMemory = async () => {
    if (!confirmClear) {
      setConfirmClear(true)
      return
    }
    setAction('clear')
    try {
      await memoryApi.clear(true)
      setConfirmClear(false)
      await Promise.allSettled([overview.refetch(), facts.refetch(), episodes.refetch(),
        patterns.refetch(), suggestions.refetch(), recall.refetch(), qc.invalidateQueries()])
    } finally {
      setAction(null)
    }
  }

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div className="flex items-end justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-2xl font-semibold text-text-primary mb-1">Memory Lab</h1>
          <p className="text-text-muted text-sm">
            Temporal facts, episodic experiences, consolidation, and learning profile.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={runConsolidate}
            disabled={!!action}
            className="flex items-center gap-2 rounded-lg border border-border bg-surface px-3 py-1.5 text-xs font-medium text-text-primary hover:border-accent/50 transition-colors cursor-pointer disabled:opacity-50"
          >
            {action === 'consolidate' ? (
              <Loader2 className="w-3.5 h-3.5 animate-spin text-accent" />
            ) : (
              <Zap className="w-3.5 h-3.5 text-accent" />
            )}
            Consolidate Now
          </button>
          <button
            onClick={clearMemory}
            disabled={!!action}
            className={`flex items-center gap-2 rounded-lg border px-3 py-1.5 text-xs font-medium transition-colors cursor-pointer disabled:opacity-50 ${
              confirmClear
                ? 'border-error/60 bg-error/15 text-error'
                : 'border-border bg-surface text-text-muted hover:border-error/50 hover:text-error'
            }`}
          >
            {action === 'clear' ? (
              <Loader2 className="w-3.5 h-3.5 animate-spin text-error" />
            ) : (
              <Trash2 className="w-3.5 h-3.5" />
            )}
            {confirmClear ? 'Confirm wipe?' : 'Clear Memory'}
          </button>
        </div>
      </div>

      {/* Overview strip */}
      <section className="rounded-lg border border-border bg-surface p-4">
        {!d ? (
          <p className="text-xs text-text-muted flex items-center gap-2">
            <Loader2 className="w-3.5 h-3.5 animate-spin text-accent" /> Loading memory…
          </p>
        ) : !d.initialized ? (
          <div className="space-y-1">
            <p className="text-sm text-text-primary flex items-center gap-2">
              <Database className="w-4 h-4 text-accent" /> Memory not built yet
            </p>
            <p className="text-xs text-text-muted">
              Memory builds from usage — open files, run audits, and search to start
              recording episodes and facts. Run “Consolidate Now” once enough experiences accumulate.
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <Stat label="Facts" value={d.facts_n} />
            <Stat label="Episodes" value={d.episodes_n} />
            <Stat label="Patterns" value={d.patterns_n} />
            <Stat label="Profiles" value={d.profiles} />
          </div>
        )}
      </section>

      {/* Tabs */}
      <div className="flex gap-1 border-b border-border">
        {TABS.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            onClick={() => setTab(id)}
            className={`flex items-center gap-1.5 px-3 py-2 text-xs font-medium -mb-px border-b-2 transition-colors cursor-pointer ${
              tab === id
                ? 'border-accent text-accent'
                : 'border-transparent text-text-muted hover:text-text-primary'
            }`}
          >
            <Icon className="w-3.5 h-3.5" /> {label}
          </button>
        ))}
      </div>

      {/* Tab bodies */}
      {tab === 'facts' && <FactsTab query={facts} />}
      {tab === 'episodes' && <EpisodesTab query={episodes} />}
      {tab === 'patterns' && <PatternsTab query={patterns} />}
      {tab === 'profile' && <ProfileTab query={suggestions} />}
      {tab === 'recall' && <RecallTab />}
    </div>
  )
}

function Stat({ label, value }: { label: string; value: number }) {
  return (
    <div>
      <p className="text-xl font-semibold font-mono text-text-primary">{value ?? '—'}</p>
      <p className="text-[10px] uppercase tracking-wider text-text-muted">{label}</p>
    </div>
  )
}

function Loading() {
  return (
    <p className="flex items-center gap-2 text-xs text-text-muted py-4">
      <Loader2 className="w-3.5 h-3.5 animate-spin text-accent" /> Loading…
    </p>
  )
}

function Empty({ children }: { children: React.ReactNode }) {
  return <p className="text-xs text-text-muted py-4">{children}</p>
}

// ── Tab: Temporal Graph ──────────────────────────────────────────────────────
function FactsTab({ query }: { query: ReturnType<typeof useQuery<{ facts: MemoryFact[] }>> }) {
  const facts = query.data?.facts
  if (query.isLoading) return <Loading />
  if (!facts || facts.length === 0)
    return <Empty>No temporal facts yet. Facts are written by the learning system from your usage.</Empty>
  return (
    <div className="space-y-2 py-3">
      {facts.map((f, i) => (
        <FactCard key={i} f={f} />
      ))}
    </div>
  )
}

function FactCard({ f }: { f: MemoryFact }) {
  const from = new Date(f.valid_from * 1000)
  const until = f.valid_until ? new Date(f.valid_until * 1000) : null
  const conf = Math.round((f.confidence ?? 0) * 100)
  return (
    <div className="rounded-lg border border-border bg-surface p-3">
      <div className="flex items-center gap-2 text-xs flex-wrap">
        <span className="font-mono text-accent">{f.subject}</span>
        <span className="text-text-muted">→</span>
        <span className="font-mono text-text-primary">{f.predicate}</span>
        <span className="text-text-muted">→</span>
        <code className="text-[11px] text-success bg-success/10 px-1.5 py-0.5 rounded">
          {typeof f.object_value === 'string' ? f.object_value : JSON.stringify(f.object_value)}
        </code>
        <span
          className={`ml-auto text-[10px] px-1.5 py-0.5 rounded border ${
            conf >= 70 ? 'bg-success/15 text-success border-success/40'
              : conf >= 40 ? 'bg-warning/15 text-warning border-warning/40'
              : 'bg-zinc-500/15 text-text-muted border-border'
          }`}
        >
          {conf}% conf
        </span>
        <span className="text-[10px] px-1.5 py-0.5 rounded bg-zinc-500/10 text-text-muted font-mono">
          {f.source}
        </span>
      </div>
      <div className="mt-2 flex items-center gap-2 text-[10px] font-mono text-text-muted">
        <Circle className="w-2 h-2 fill-current text-success" />
        <span>{from.toLocaleString()}</span>
        {until ? (
          <>
            <span className="text-text-muted">→ expires</span>
            <span>{until.toLocaleString()}</span>
          </>
        ) : (
          <span className="text-accent">valid</span>
        )}
      </div>
    </div>
  )
}

// ── Tab: Episodes ────────────────────────────────────────────────────────────
const EPISODE_TONE: Record<string, string> = {
  error: 'bg-error/15 text-error border-error/40',
  success: 'bg-success/15 text-success border-success/40',
  interaction: 'bg-accent/15 text-accent border-accent/40',
  debug: 'bg-warning/15 text-warning border-warning/40',
}

function EpisodesTab({ query }: { query: ReturnType<typeof useQuery<{ episodes: MemoryEpisode[] }>> }) {
  const eps = query.data?.episodes
  if (query.isLoading) return <Loading />
  if (!eps || eps.length === 0)
    return <Empty>No episodes yet. Episodes record interactions, successes, and errors from your usage.</Empty>
  return (
    <div className="py-3 rounded-lg border border-border bg-surface overflow-hidden">
      <table className="w-full text-left text-xs">
        <thead className="bg-surface-raised text-[10px] uppercase tracking-wider text-text-muted">
          <tr>
            <th className="px-3 py-2">Type</th>
            <th className="px-3 py-2">Timestamp</th>
            <th className="px-3 py-2">Context</th>
            <th className="px-3 py-2">Outcome</th>
            <th className="px-3 py-2">Embedding</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-border-subtle">
          {eps.map((e) => (
            <tr key={e.id} className="hover:bg-surface-raised/40 transition-colors">
              <td className="px-3 py-2">
                <span
                  className={`px-1.5 py-0.5 rounded text-[10px] font-medium border capitalize ${EPISODE_TONE[e.episode_type] ?? 'bg-zinc-500/15 text-text-muted border-border'}`}
                >
                  {e.episode_type}
                </span>
              </td>
              <td className="px-3 py-2 font-mono text-text-muted">
                {new Date(e.timestamp * 1000).toLocaleString()}
              </td>
              <td className="px-3 py-2">
                <code className="text-[10px] text-text-muted line-clamp-2">
                  {JSON.stringify(e.context)}
                </code>
              </td>
              <td className="px-3 py-2 text-text-secondary">{e.outcome ?? '—'}</td>
              <td className="px-3 py-2">
                {e.has_embedding ? (
                  <span className="text-[10px] text-success">yes</span>
                ) : (
                  <span className="text-[10px] text-text-muted">no</span>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <p className="px-3 py-2 text-[10px] text-text-muted border-t border-border-subtle">
        “Embedding: no” — the embedder is off (web never loads it); recall-similar falls back to
        keyword match (CORE-33).
      </p>
    </div>
  )
}

// ── Tab: Patterns ───────────────────────────────────────────────────────────
function PatternsTab({ query }: { query: ReturnType<typeof useQuery<{
  analyzed: Record<string, unknown> | null; learned: MemoryFact[]
}>> }) {
  const a = query.data?.analyzed
  const learned = query.data?.learned
  if (query.isLoading) return <Loading />
  if (!a && (!learned || learned.length === 0))
    return <Empty>No patterns yet. Run “Consolidate Now” to promote recurring experiences into
      learned patterns.</Empty>
  return (
    <div className="space-y-4 py-3">
      {learned && learned.length > 0 && (
        <section>
          <h3 className="text-xs font-medium text-text-secondary mb-2">Promoted learned patterns</h3>
          <div className="space-y-2">
            {learned.map((f, i) => (
              <FactCard key={i} f={f} />
            ))}
          </div>
        </section>
      )}
      {a && (
        <section>
          <h3 className="text-xs font-medium text-text-secondary mb-2">Analyzed usage patterns</h3>
          <PreJSON value={a} />
        </section>
      )}
    </div>
  )
}

// ── Tab: Learning Profile ───────────────────────────────────────────────────
function ProfileTab({ query }: { query: ReturnType<typeof useQuery<{
  suggestions: { action: string; reason?: string; confidence?: number; score?: number; source?: string }[]
}>> }) {
  const s = query.data?.suggestions
  if (query.isLoading) return <Loading />
  if (!s || s.length === 0)
    return <Empty>No personalized suggestions yet — they appear as CIP learns your workflow.
      Profile: <span className="font-mono text-accent">default</span> (single-user v1).</Empty>
  return (
    <div className="py-3 space-y-2">
      <p className="text-xs text-text-muted">
        Profile: <span className="font-mono text-accent">default</span> · personalized for your command
        history, time patterns, and suggestion acceptance.
      </p>
      {s.map((item, i) => (
        <div key={i} className="rounded-lg border border-border bg-surface p-3">
          <div className="flex items-center gap-2">
            <code className="text-xs text-accent">{item.action}</code>
            <span className="ml-auto text-[10px] font-mono text-text-muted">
              {item.source ?? 'suggestion'}
            </span>
          </div>
          {item.reason && <p className="text-[11px] text-text-muted mt-1">{item.reason}</p>}
          {item.score !== undefined && (
            <div className="mt-1.5 flex items-center gap-1">
              <div className="flex-1 h-1 rounded-full bg-border/60 overflow-hidden">
                <div
                  className="h-full rounded-full bg-accent"
                  style={{ width: `${Math.min(100, (item.score ?? 0) * 100)}%` }}
                />
              </div>
              <span className="text-[9px] font-mono text-text-muted">
                {(item.score ?? 0).toFixed(2)}
              </span>
            </div>
          )}
        </div>
      ))}
    </div>
  )
}

// ── Tab: Recall ─────────────────────────────────────────────────────────────
function RecallTab() {
  const [q, setQ] = useState('')
  const [sent, setSent] = useState('')
  const recall = useQuery({
    queryKey: ['memory-recall', sent],
    queryFn: () => memoryApi.recall(sent),
    enabled: sent.length > 0,
  })
  const results = recall.data?.results

  return (
    <div className="py-3 space-y-3">
      <form
        onSubmit={(e) => {
          e.preventDefault()
          setSent(q.trim())
        }}
        className="flex gap-2"
      >
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="What did I do last time… e.g. audit, search, sync"
          className="flex-1 rounded-lg border border-border bg-surface px-3 py-2 text-sm text-text-primary placeholder:text-text-muted focus:outline-none focus:border-accent/50"
        />
        <button
          type="submit"
          className="flex items-center gap-2 rounded-lg border border-border bg-surface px-3 py-2 text-xs font-medium text-text-primary hover:border-accent/50 transition-colors cursor-pointer"
        >
          <Search className="w-3.5 h-3.5 text-accent" /> Recall
        </button>
      </form>
      {recall.isLoading && <Loading />}
      {sent && results && results.length === 0 && (
        <Empty>No matching experiences for “{sent}”.</Empty>
      )}
      {results && results.length > 0 && (
        <div className="space-y-2">
          {results.map((r, i) => (
            <RecallCard key={i} r={r} />
          ))}
        </div>
      )}
    </div>
  )
}

function RecallCard({ r }: { r: RecallResult }) {
  const tone = r.type === 'episode' ? 'bg-accent/15 text-accent border-accent/40'
    : 'bg-warning/15 text-warning border-warning/40'
  return (
    <div className="rounded-lg border border-border bg-surface p-3">
      <div className="flex items-center gap-2 text-[10px]">
        <span className={`px-1.5 py-0.5 rounded border font-medium capitalize ${tone}`}>
          {r.type}
        </span>
        <span className="font-mono text-text-muted">
          {new Date(r.timestamp * 1000).toLocaleString()}
        </span>
        {r.outcome && <span className="text-text-secondary">· {r.outcome}</span>}
      </div>
      <pre className="mt-2 text-[10px] text-text-muted whitespace-pre-wrap">
        {typeof r.content === 'string' ? r.content : JSON.stringify(r.content, null, 1)}
      </pre>
    </div>
  )
}

function PreJSON({ value }: { value: unknown }) {
  return (
    <div className="rounded-lg border border-border bg-surface p-3 text-[10px] font-mono text-text-muted whitespace-pre-wrap">
      {JSON.stringify(value, null, 1)}
    </div>
  )
}