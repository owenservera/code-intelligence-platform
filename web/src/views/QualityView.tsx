import { useQuery } from '@tanstack/react-query'
import { auditApi, type QualityBundle, type QualityFinding, type Severity } from '@/lib/api'
import { RefreshCw, Loader2, Zap, AlertTriangle, Gauge, HeartPulse } from 'lucide-react'
import { useState } from 'react'

const SEVERITY_ORDER: Severity[] = ['critical', 'high', 'medium', 'low']
const SEVERITY_STYLE: Record<Severity, string> = {
  critical: 'bg-error/15 text-error border-error/40',
  high: 'bg-warning/15 text-warning border-warning/40',
  medium: 'bg-accent/15 text-accent border-accent/40',
  low: 'bg-zinc-500/15 text-text-muted border-border',
}

export function QualityView() {
  const [filter, setFilter] = useState<Severity | 'all'>('all')
  const [action, setAction] = useState<string | null>(null)

  const bundle = useQuery({
    queryKey: ['quality-bundle'],
    queryFn: auditApi.bundle,
    refetchInterval: 30_000,
  })

  const findings = useQuery({
    queryKey: ['quality-findings', filter],
    queryFn: () =>
      auditApi.findings({ severity: filter === 'all' ? undefined : filter, limit: 50 }),
  })

  const quickWins = useQuery({
    queryKey: ['quality-quickwins'],
    queryFn: () => auditApi.quickWins(10),
    refetchInterval: 30_000,
  })

  const d = bundle.data

  const runAudit = async () => {
    setAction('audit')
    try {
      await auditApi.runAudit()
      await bundle.refetch()
    } finally {
      setAction(null)
    }
  }

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div className="flex items-end justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-text-primary mb-1">Quality & Audit</h1>
          <p className="text-text-muted text-sm">Repo health, findings, and quick wins.</p>
        </div>
        <button
          onClick={runAudit}
          disabled={!!action}
          className="flex items-center gap-2 rounded-lg border border-border bg-surface px-3 py-1.5 text-xs font-medium text-text-primary hover:border-accent/50 transition-colors cursor-pointer disabled:opacity-50"
        >
          {action ? (
            <Loader2 className="w-3.5 h-3.5 animate-spin text-accent" />
          ) : (
            <RefreshCw className="w-3.5 h-3.5 text-accent" />
          )}
          Run Audit
        </button>
      </div>

      {/* Score ring + breakdown */}
      <ScoreCard d={d} />

      {/* Summary chips */}
      <section className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <SummaryChip
          icon={AlertTriangle}
          label="Critical"
          value={d?.health.critical_issues}
          tone="error"
        />
        <SummaryChip
          icon={Zap}
          label="High Priority"
          value={d?.health.high_priority}
          tone="warning"
        />
        <SummaryChip
          icon={Gauge}
          label="Tech Debt"
          value={d?.health.technical_debt}
          tone="accent"
        />
        <SummaryChip
          icon={HeartPulse}
          label="Open Findings"
          value={d?.findings.open}
          tone="muted"
        />
      </section>

      {/* Findings table */}
      <section className="space-y-3">
        <div className="flex items-center gap-2 flex-wrap">
          <h2 className="text-sm font-medium text-text-secondary mr-auto">Findings</h2>
          {['all', ...SEVERITY_ORDER].map((s) => (
            <button
              key={s}
              onClick={() => setFilter(s as Severity | 'all')}
              className={`px-2.5 py-1 rounded-full text-[11px] font-medium border transition-colors cursor-pointer capitalize ${
                filter === s
                  ? s === 'all'
                    ? 'bg-accent/20 text-accent border-accent/50'
                    : SEVERITY_STYLE[s as Severity]
                  : 'border-border-subtle text-text-muted hover:border-border'
              }`}
            >
              {s}
            </button>
          ))}
        </div>
        <FindingsTable findings={findings.data?.findings} count={findings.data?.count} />
      </section>

      {/* Quick wins */}
      <section>
        <h2 className="text-sm font-medium text-text-secondary mb-3">Quick Wins</h2>
        <QuickWinsList wins={quickWins.data?.quick_wins} />
      </section>
    </div>
  )
}

function ScoreCard({ d }: { d?: QualityBundle }) {
  const score = d?.health.overall_score
  const parts = d?.breakdown
  if (!score || !parts) {
    return (
      <section className="rounded-lg border border-border bg-surface p-5 flex items-center gap-3">
        <Loader2 className="w-4 h-4 animate-spin text-accent" /> Loading health…
      </section>
    )
  }
  const tone =
    score >= 80 ? 'text-success' : score >= 60 ? 'text-warning' : 'text-error'
  const r = 34
  const c = 2 * Math.PI * r
  const filled = (score / 100) * c
  return (
    <section className="rounded-lg border border-border bg-surface p-5 grid md:grid-cols-[auto_1fr] gap-6 items-center">
      <div className="relative w-24 h-24">
        <svg viewBox="0 0 80 80" className="w-24 h-24 -rotate-90">
          <circle cx="40" cy="40" r={r} fill="none" strokeWidth="8" className="stroke-border" />
          <circle
            cx="40"
            cy="40"
            r={r}
            fill="none"
            strokeWidth="8"
            strokeLinecap="round"
            strokeDasharray={`${filled} ${c - filled}`}
            className="stroke-accent"
          />
        </svg>
        <div className="absolute inset-0 flex items-center justify-center">
          <span className={`text-2xl font-semibold font-mono ${tone}`}>{Math.round(score)}</span>
        </div>
      </div>
      <div className="space-y-2.5">
        <p className="text-xs text-text-muted uppercase tracking-wider">Health Score</p>
        <Bar label="Coverage" value={parts.coverage} />
        <Bar label="Quality" value={parts.quality} />
        <Bar label="Freshness" value={parts.freshness} />
        {parts.complexity !== null && parts.complexity !== undefined && (
          <Bar label="Complexity" value={parts.complexity} />
        )}
        {d && (
          <p className="text-[10px] font-mono text-text-muted">
            generated in {d.generated_ms}ms
          </p>
        )}
      </div>
    </section>
  )
}

function Bar({ label, value }: { label: string; value: number }) {
  const tone = value >= 80 ? 'bg-success' : value >= 50 ? 'bg-warning' : 'bg-error'
  return (
    <div className="flex items-center gap-2">
      <span className="w-20 text-[10px] text-text-muted">{label}</span>
      <div className="flex-1 h-1.5 rounded-full bg-border/60 overflow-hidden">
        <div className={`h-full rounded-full ${tone}`} style={{ width: `${Math.min(100, value)}%` }} />
      </div>
      <span className="w-10 text-right text-[10px] font-mono text-text-secondary">{value}%</span>
    </div>
  )
}

function SummaryChip({
  icon: Icon,
  label,
  value,
  tone,
}: {
  icon: React.ComponentType<{ className?: string }>
  label: string
  value?: number
  tone: 'error' | 'warning' | 'accent' | 'muted'
}) {
  const color = {
    error: 'text-error',
    warning: 'text-warning',
    accent: 'text-accent',
    muted: 'text-text-muted',
  }[tone]
  return (
    <div className="rounded-lg border border-border bg-surface p-4 flex items-center gap-3">
      <Icon className={`w-4 h-4 ${color}`} />
      <div>
        <p className="text-lg font-semibold font-mono text-text-primary">
          {value ?? '—'}
        </p>
        <p className="text-[10px] uppercase tracking-wider text-text-muted">{label}</p>
      </div>
    </div>
  )
}

function FindingsTable({ findings, count }: { findings?: QualityFinding[]; count?: number }) {
  if (!findings) return <p className="text-xs text-text-muted">Loading findings…</p>
  if (findings.length === 0)
    return <p className="text-xs text-text-muted">No findings for this filter.</p>
  return (
    <div className="rounded-lg border border-border bg-surface overflow-hidden">
      <table className="w-full text-left text-xs">
        <thead className="bg-surface-raised text-[10px] uppercase tracking-wider text-text-muted">
          <tr>
            <th className="px-3 py-2">Severity</th>
            <th className="px-3 py-2">Rule</th>
            <th className="px-3 py-2">Title</th>
            <th className="px-3 py-2">Path</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-border-subtle">
          {findings.map((f) => (
            <tr key={f.id} className="hover:bg-surface-raised/40 transition-colors">
              <td className="px-3 py-2">
                <span
                  className={`px-1.5 py-0.5 rounded text-[10px] font-medium border capitalize ${SEVERITY_STYLE[f.severity]}`}
                >
                  {f.severity}
                </span>
              </td>
              <td className="px-3 py-2 font-mono text-accent">{f.rule}</td>
              <td className="px-3 py-2">
                <p className="text-text-primary">{f.title}</p>
                {f.suggestion && (
                  <p className="text-[10px] text-text-muted mt-0.5 line-clamp-2">{f.suggestion}</p>
                )}
              </td>
              <td className="px-3 py-2 font-mono text-text-muted">{f.path}</td>
            </tr>
          ))}
        </tbody>
      </table>
      {count !== undefined && count > (findings.length ?? 0) && (
        <div className="px-3 py-2 text-[10px] text-text-muted border-t border-border-subtle">
          showing {findings.length} of {count} — refine the filter for more
        </div>
      )}
    </div>
  )
}

function QuickWinsList({ wins }: { wins?: QualityBundle['quick_wins'] }) {
  if (!wins) return <p className="text-xs text-text-muted">Loading quick wins…</p>
  if (wins.length === 0) return <p className="text-xs text-text-muted">No quick wins.</p>
  return (
    <div className="space-y-2">
      {wins.map((w) => (
        <div
          key={w.id}
          className="rounded-lg border border-border bg-surface p-3 flex items-start gap-3"
        >
          <span className={`mt-0.5 px-1.5 py-0.5 rounded text-[10px] font-medium border capitalize ${SEVERITY_STYLE[w.severity]}`}>
            {w.effort}
          </span>
          <div className="min-w-0">
            <p className="text-xs text-text-primary">{w.title}</p>
            <p className="text-[10px] text-text-muted mt-0.5 line-clamp-2">{w.suggestion}</p>
            <p className="text-[10px] font-mono text-text-muted mt-1">{w.path}</p>
          </div>
        </div>
      ))}
    </div>
  )
}