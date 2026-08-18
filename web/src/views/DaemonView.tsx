import { useQuery } from '@tanstack/react-query'
import { daemonApi, embedApi } from '@/lib/api'
import { useAppStore } from '@/stores/app'
import { Play, Square, RotateCcw, Activity, Wifi, Loader2 } from 'lucide-react'
import { useState } from 'react'

export function DaemonView() {
  const status = useAppStore((s) => s.status)
  const [action, setAction] = useState<string | null>(null)

  const daemon = useQuery({
    queryKey: ['daemon-status'],
    queryFn: daemonApi.status,
    refetchInterval: 5_000,
  })
  const embed = useQuery({
    queryKey: ['embed-status'],
    queryFn: embedApi.status,
    refetchInterval: 10_000,
  })
  const log = useQuery({
    queryKey: ['daemon-log'],
    queryFn: () => daemonApi.log(200),
    refetchInterval: 30_000,
  })

  const d = daemon.data
  const e = embed.data

  const run = async (name: string, fn: () => Promise<unknown>) => {
    setAction(name)
    try {
      await fn()
      await Promise.allSettled([daemon.refetch(), embed.refetch()])
    } finally {
      setAction(null)
    }
  }

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-text-primary mb-1">Daemon & Server Management</h1>
        <p className="text-text-muted text-sm">Control the embedding daemon and watch its log.</p>
      </div>

      {/* Daemon panel */}
      <section className="space-y-3">
        <h2 className="text-sm font-medium text-text-secondary">Daemon</h2>
        <div className="rounded-lg border border-border bg-surface p-5 space-y-4">
          <div className="flex items-center gap-3">
            <Wifi className={`w-5 h-5 ${d?.alive ? 'text-success' : 'text-error'}`} />
            <div>
              <p className="text-sm text-text-primary font-medium">
                {d?.alive ? 'Running' : 'Stopped'}
              </p>
              <p className="text-xs font-mono text-text-muted">
                pid: {d?.pid ?? '—'} · port: {d?.port ?? '—'} ·{' '}
                {d?.warm ? 'warm' : 'not warm'}
              </p>
            </div>
            <div className="flex-1" />
            <div className="flex gap-2">
              {!d?.alive && (
                <Button onClick={() => run('start', () => daemonApi.start(d?.port ?? 8787))} disabled={!!action}>
                  {action === 'start' ? <Loader2 className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
                  Start
                </Button>
              )}
              {d?.alive && (
                <>
                  <Button variant="danger" onClick={() => run('stop', () => daemonApi.stop())} disabled={!!action}>
                    {action === 'stop' ? <Loader2 className="w-4 h-4 animate-spin" /> : <Square className="w-4 h-4" />}
                    Stop
                  </Button>
                  <Button onClick={() => run('restart', () => daemonApi.restart(d?.port ?? 8787))} disabled={!!action}>
                    {action === 'restart' ? <Loader2 className="w-4 h-4 animate-spin" /> : <RotateCcw className="w-4 h-4" />}
                    Restart
                  </Button>
                </>
              )}
            </div>
          </div>

          {d?.health && (
            <div className="grid grid-cols-4 gap-3 text-xs">
              <Metric label="Model" value={String(d.health.model ?? '—')} mono />
              <Metric label="Dim" value={String(d.health.dim ?? '—')} mono />
              <Metric label="Uptime" value={d.health.uptime_s != null ? `${Math.round(d.health.uptime_s)}s` : '—'} mono />
              <Metric label="State" value={d.warm ? 'warm' : 'cold'} mono />
            </div>
          )}
        </div>
      </section>

      {/* Embedding service panel */}
      <section className="space-y-3">
        <h2 className="text-sm font-medium text-text-secondary">Embedding Service</h2>
        <div className="rounded-lg border border-border bg-surface p-5">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-xs">
            <Metric label="Backend" value={e?.backend ?? '—'} mono />
            <Metric label="Resolution" value={e?.resolution ?? '—'} mono />
            <Metric label="Model" value={e?.model ?? '—'} mono />
            <Metric label="Dim" value={e?.dim ? String(e.dim) : '—'} mono />
            <Metric label="Warm" value={e?.warm ? 'yes' : 'no'} mono />
            <Metric label="Latency" value={e?.latency_ms != null ? `${e.latency_ms}ms` : '—'} mono />
            <Metric label="Effective backend" value={e?.effective_backend ?? '—'} mono />
            <Metric label="Status cluster" value={status.embedder} mono />
          </div>
        </div>
      </section>

      {/* Log tail */}
      <section className="space-y-3">
        <h2 className="text-sm font-medium text-text-secondary flex items-center gap-2">
          <Activity className="w-4 h-4" /> Daemon Log
        </h2>
        <div className="rounded-lg border border-border bg-black/60 p-4 font-mono text-[11px] leading-5 text-zinc-300 max-h-80 overflow-y-auto">
          {log.data?.lines.length ? (
            log.data.lines.map((l, i) => <div key={i}>{l}</div>)
          ) : (
            <p className="text-text-muted">No daemon log yet. Start the daemon to see output.</p>
          )}
        </div>
      </section>
    </div>
  )
}

function Metric({ label, value, mono }: { label: string; value: string; mono?: boolean }) {
  return (
    <div className="min-w-0">
      <p className="text-[10px] uppercase tracking-wider text-text-muted mb-0.5">{label}</p>
      <p className={`text-text-primary truncate ${mono ? 'font-mono' : ''}`}>{value}</p>
    </div>
  )
}

function Button({
  children,
  variant,
  onClick,
  disabled,
}: {
  children: React.ReactNode
  variant?: 'default' | 'danger'
  onClick?: () => void
  disabled?: boolean
}) {
  const cls =
    variant === 'danger'
      ? 'border-error/40 text-error hover:bg-error/10'
      : 'border-border text-text-primary hover:bg-surface-raised'
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md border bg-surface text-xs transition-colors cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed ${cls}`}
    >
      {children}
    </button>
  )
}