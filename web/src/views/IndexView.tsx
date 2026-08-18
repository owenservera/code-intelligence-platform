import { useMutation, useQuery } from '@tanstack/react-query'
import { indexApi, watchApi, snapshotsApi, type AdmissionReport, type Snapshot } from '@/lib/api'
import { useAppStore } from '@/stores/app'
import { ActivityFeed } from '@/components/jobs/ActivityFeed'
import { RefreshCw, Database, Loader2, ShieldAlert, Trash2, ClipboardCheck, Eye, EyeOff, History } from 'lucide-react'
import { useState } from 'react'

export function IndexView() {
  const [action, setAction] = useState<string | null>(null)
  const [confirm, setConfirm] = useState<string | null>(null)
  const [watchMsg, setWatchMsg] = useState<string | null>(null)
  const [snapDetail, setSnapDetail] = useState<Snapshot | null>(null)
  const status = useAppStore((s) => s.status)

  const index = useQuery({
    queryKey: ['index-status'],
    queryFn: indexApi.status,
    refetchInterval: 5_000,
  })
  const admission = useQuery({
    queryKey: ['admission'],
    queryFn: indexApi.admission,
  })

  const watch = useQuery({
    queryKey: ['watch-status'],
    queryFn: watchApi.status,
    refetchInterval: 3_000,
  })
  const watchStart = useMutation({
    mutationFn: watchApi.start,
    onSuccess: () => {
      setWatchMsg('watching for changes')
      watch.refetch()
    },
  })
  const watchStop = useMutation({
    mutationFn: watchApi.stop,
    onSuccess: () => {
      setWatchMsg('watch stopped')
      watch.refetch()
    },
  })

  const snapshots = useQuery({
    queryKey: ['snapshots'],
    queryFn: () => snapshotsApi.list(undefined, 12),
    refetchInterval: 30_000,
  })

  const d = index.data

  const run = async (name: string, fn: () => Promise<unknown>) => {
    setAction(name)
    try {
      await fn()
      await Promise.allSettled([index.refetch(), admission.refetch()])
    } finally {
      setAction(null)
    }
  }

  const confirmThen = (name: string, fn: () => Promise<unknown>) => {
    if (confirm !== name) {
      setConfirm(name)
      return
    }
    setConfirm(null)
    run(name, fn)
  }

  const freshness = d?.fresh ? 'fresh' : d?.last_sync ? 'stale' : 'never'

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-text-primary mb-1">Index Management</h1>
        <p className="text-text-muted text-sm">Live index stats and maintenance jobs.</p>
      </div>

      {/* Live activity (GAP-07: watch.event / index.update delta lines) */}
      <ActivityFeed />

      {/* Live counters */}
      <section className="rounded-lg border border-border bg-surface p-5">
        <div className="flex items-center gap-2 mb-4">
          <Database className="w-4 h-4 text-accent" />
          <h2 className="text-sm font-medium text-text-primary">Index Stats</h2>
          <span
            className={`ml-auto text-[10px] px-2 py-0.5 rounded-full font-mono ${
              freshness === 'fresh' ? 'bg-success/15 text-success' :
              freshness === 'stale' ? 'bg-warning/15 text-warning' :
              'bg-error/15 text-error'
            }`}
          >
            {freshness}
          </span>
        </div>
        <div className="grid grid-cols-3 md:grid-cols-5 gap-4">
          <Counter label="Files" value={d?.files} />
          <Counter label="Symbols" value={d?.symbols} />
          <Counter label="Chunks" value={d?.chunks} />
          <Counter label="Edges" value={d?.edges} />
          <Counter label="Vectors" value={d?.vectors} />
        </div>
        <div className="mt-4 flex items-center gap-4 text-[11px] font-mono text-text-muted">
          {d?.last_sync ? (
            <span>last sync: {new Date(d.last_sync * 1000).toLocaleTimeString()}</span>
          ) : (
            <span>never synced</span>
          )}
          {d && (
            <span className="flex items-center gap-1">
              <StatusDot level={status.index} /> {status.indexAge ?? 'no index'}
            </span>
          )}
        </div>
      </section>

      {/* Maintenance actions */}
      <section className="space-y-3">
        <h2 className="text-sm font-medium text-text-secondary">Maintenance</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <ActionCard
            icon={RefreshCw}
            name="Sync"
            desc="Incremental index update"
            busy={action === 'sync'}
            disabled={!!action}
            onClick={() => run('sync', () => indexApi.sync(false))}
            onConfirm={() => confirmThen('sync', () => indexApi.sync(false))}
            confirm={confirm === 'sync'}
          />
          <ActionCard
            icon={Database}
            name="Full Sync"
            desc="Reindex everything"
            busy={action === 'full-sync'}
            disabled={!!action}
            onClick={() => confirmThen('full-sync', () => indexApi.sync(true))}
            onConfirm={() => confirmThen('full-sync', () => indexApi.sync(true))}
            confirm={confirm === 'full-sync'}
            warn
          />
          <ActionCard
            icon={ClipboardCheck}
            name="Verify"
            desc="Check index drift"
            busy={action === 'verify'}
            disabled={!!action}
            onClick={() => run('verify', () => indexApi.verify(false))}
            onConfirm={() => confirmThen('verify', () => indexApi.verify(false))}
            confirm={confirm === 'verify'}
          />
          <ActionCard
            icon={Trash2}
            name="Vacuum"
            desc="Prune events & orphans"
            busy={action === 'vacuum'}
            disabled={!!action}
            onClick={() => confirmThen('vacuum', () => indexApi.vacuum())}
            onConfirm={() => confirmThen('vacuum', () => indexApi.vacuum())}
            confirm={confirm === 'vacuum'}
            warn
          />
        </div>
        {action && (
          <p className="flex items-center gap-2 text-xs text-text-muted">
            <Loader2 className="w-3.5 h-3.5 animate-spin text-accent" /> Job
            running… watch the status chip
          </p>
        )}
        {action === 'rebuild' && (
          <p className="text-xs text-warning flex items-center gap-2">
            <ShieldAlert className="w-4 h-4" /> Rebuild wipes the DB first. This is destructive.
          </p>
        )}
      </section>

      {/* Filesystem watch (SPEC-04 §6.2 / CORE-16) */}
      <section className="rounded-lg border border-border bg-surface p-5">
        <div className="flex items-center gap-2 mb-3">
          <Eye className="w-4 h-4 text-accent" />
          <h2 className="text-sm font-medium text-text-primary">Filesystem Watch</h2>
          <span
            className={`ml-auto text-[10px] px-2 py-0.5 rounded-full font-mono ${
              watch.data?.running ? 'bg-success/15 text-success' : 'bg-zinc-500/15 text-text-muted'
            }`}
          >
            {watch.data?.stopping ? 'stopping…' : watch.data?.running ? 'watching' : 'idle'}
          </span>
        </div>
        <p className="text-[11px] text-text-muted mb-3">
          Auto re-syncs the index when files change. Polling interval:{' '}
          <span className="font-mono">{watch.data?.interval ?? 1.0}s</span>.
        </p>
        <div className="flex items-center gap-3">
          {watch.data?.running ? (
            <button
              onClick={() => watchStop.mutate()}
              disabled={watchStop.isPending}
              className="inline-flex items-center gap-2 rounded-md border border-warning/40 bg-warning/10 px-3 py-1.5 text-xs font-medium text-warning hover:border-warning/70 transition-colors cursor-pointer disabled:opacity-50"
            >
              <EyeOff className="w-3.5 h-3.5" />
              {watchStop.isPending ? 'Stopping…' : 'Stop Watch'}
            </button>
          ) : (
            <button
              onClick={() => watchStart.mutate(1.0)}
              disabled={watchStart.isPending || watch.data?.stopping}
              className="inline-flex items-center gap-2 rounded-md border border-border-subtle bg-surface px-3 py-1.5 text-xs font-medium text-text-primary hover:border-border transition-colors cursor-pointer disabled:opacity-50"
            >
              <Eye className="w-3.5 h-3.5" />
              {watchStart.isPending ? 'Starting…' : 'Start Watch'}
            </button>
          )}
          {watchMsg && <span className="text-[11px] text-text-muted">{watchMsg}</span>}
        </div>
      </section>

      {/* Snapshot history (SPEC-04 §6.1 / CORE-17) */}
      <section className="rounded-lg border border-border bg-surface p-5">
        <div className="flex items-center gap-2 mb-3">
          <History className="w-4 h-4 text-accent" />
          <h2 className="text-sm font-medium text-text-primary">Snapshot History</h2>
          <span className="ml-auto text-[10px] px-2 py-0.5 rounded-full font-mono bg-zinc-500/15 text-text-muted">
            {snapshots.data?.count ?? '—'} rows
          </span>
        </div>
        {snapshots.isLoading ? (
          <p className="flex items-center gap-2 text-xs text-text-muted">
            <Loader2 className="w-3.5 h-3.5 animate-spin text-accent" /> Loading snapshots…
          </p>
        ) : snapshots.data?.snapshots.length ? (
          <div className="space-y-1.5">
            {snapshots.data.snapshots.map((s) => (
              <button
                key={s.ts}
                onClick={() => setSnapDetail(snapDetail?.ts === s.ts ? null : s)}
                className={`w-full rounded-md border px-3 py-2 text-left text-xs transition-colors cursor-pointer ${
                  snapDetail?.ts === s.ts
                    ? 'border-accent/60 bg-accent/10'
                    : 'border-border-subtle bg-surface hover:border-border'
                }`}
              >
                <span className="flex items-center gap-2">
                  <span className="font-mono text-text-primary">
                    {new Date(s.ts * 1000).toLocaleString()}
                  </span>
                  <span className="px-1.5 rounded-full bg-accent/10 text-accent font-mono">
                    {s.job}
                  </span>
                  {s.health != null && (
                    <span
                      className={`px-1.5 rounded-full font-mono ${
                        s.health >= 80
                          ? 'bg-success/15 text-success'
                          : s.health >= 50
                            ? 'bg-warning/15 text-warning'
                            : 'bg-error/15 text-error'
                      }`}
                    >
                      {s.health}
                    </span>
                  )}
                  {s.counts?.files != null && (
                    <span className="ml-auto text-text-muted">
                      {s.counts.files} files · {s.counts.symbols ?? 0} syms
                    </span>
                  )}
                </span>
              </button>
            ))}
            {snapDetail && (
              <pre className="rounded-md border border-border-subtle bg-surface-raised p-3 text-[10px] font-mono text-text-secondary overflow-x-auto whitespace-pre-wrap">
                {JSON.stringify(
                  {
                    ts: snapDetail.ts,
                    job: snapDetail.job,
                    health: snapDetail.health,
                    counts: snapDetail.counts,
                    severity: snapDetail.severity,
                    meta: snapDetail.meta,
                  },
                  null,
                  2,
                )}
              </pre>
            )}
          </div>
        ) : (
          <p className="text-xs text-text-muted">
            No snapshots yet. Run a sync or audit to record the first one.
          </p>
        )}
      </section>

      {/* Admission / trust transparency */}
      <section className="space-y-3">
        <h2 className="text-sm font-medium text-text-secondary">Admission Transparency</h2>
        <AdmissionTable report={admission.data} />
      </section>
    </div>
  )
}

function Counter({ label, value }: { label: string; value?: number }) {
  return (
    <div>
      <p className="text-2xl font-semibold font-mono text-text-primary">{value ?? '—'}</p>
      <p className="text-[10px] uppercase tracking-wider text-text-muted">{label}</p>
    </div>
  )
}

function ActionCard({
  icon: Icon,
  name,
  desc,
  busy,
  disabled,
  onClick,
  onConfirm,
  confirm,
  warn,
}: {
  icon: React.ComponentType<{ className?: string }>
  name: string
  desc: string
  busy?: boolean
  disabled?: boolean
  onClick: () => void
  onConfirm: () => void
  confirm?: boolean
  warn?: boolean
}) {
  const border = confirm
    ? 'border-warning/60 bg-warning/10'
    : warn
      ? 'border-warning/30 hover:border-warning/50'
      : 'border-border-subtle hover:border-border'
  return (
    <button
      onClick={confirm ? onConfirm : onClick}
      disabled={disabled}
      className={`rounded-lg border bg-surface p-4 text-left transition-colors cursor-pointer disabled:opacity-50 ${border}`}
    >
      <div className="flex items-center gap-2 mb-1.5">
        {busy ? (
          <Loader2 className="w-4 h-4 animate-spin text-accent" />
        ) : (
          <Icon className={`w-4 h-4 ${warn ? 'text-warning' : 'text-accent'}`} />
        )}
        <span className="text-sm font-medium text-text-primary">{confirm ? 'Confirm?' : name}</span>
      </div>
      <p className="text-[11px] text-text-muted">{confirm ? 'Click to run now' : desc}</p>
    </button>
  )
}

function AdmissionTable({ report }: { report?: AdmissionReport | null }) {
  if (!report) return <p className="text-xs text-text-muted">Admission report unavailable.</p>
  return (
    <div className="rounded-lg border border-border bg-surface p-4 space-y-2 text-xs">
      <p className="text-text-secondary">
        mode: <span className="font-mono text-text-primary">{report.mode}</span>
      </p>
      <div className="flex flex-wrap gap-x-6 gap-y-1">
        {Object.entries(report.index_tiers ?? {}).map(([tier, count]) => (
          <span key={tier} className="text-text-muted">
            {tier}: <span className="font-mono text-success">{count}</span>
          </span>
        ))}
      </div>
    </div>
  )
}

function StatusDot({ level }: { level: string }) {
  const color = {
    ok: 'bg-success',
    warn: 'bg-warning',
    error: 'bg-error',
    loading: 'bg-zinc-500 animate-pulse',
  }[level] ?? 'bg-zinc-500'
  return <span className={`w-1.5 h-1.5 rounded-full inline-block ${color}`} />
}