import { useQuery } from '@tanstack/react-query'
import { auditApi, forensicsApi, type QualityBundle, type QualityFinding, type Severity } from '@/lib/api'
import {
  RefreshCw, Loader2, Zap, AlertTriangle, Gauge, HeartPulse,
  Ghost, ShieldAlert, Layers, Flame, KeyRound, ArrowRight,
  Copy, Check, FileDown, ExternalLink, Sparkles
} from 'lucide-react'
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'

const SEVERITY_ORDER: Severity[] = ['critical', 'high', 'medium', 'low']
const SEVERITY_STYLE: Record<Severity, string> = {
  critical: 'bg-error/15 text-error border-error/40',
  high: 'bg-warning/15 text-warning border-warning/40',
  medium: 'bg-accent/15 text-accent border-accent/40',
  low: 'bg-zinc-500/15 text-text-muted border-border',
}

type TabType = 'overview' | 'ghost' | 'silent' | 'architecture' | 'risk' | 'secrets'

export function QualityView() {
  const [activeTab, setActiveTab] = useState<TabType>('overview')
  const [filter, setFilter] = useState<Severity | 'all'>('all')
  const [action, setAction] = useState<string | null>(null)
  const [copiedId, setCopiedId] = useState<string | null>(null)
  const navigate = useNavigate()

  const bundle = useQuery({
    queryKey: ['quality-bundle'],
    queryFn: auditApi.bundle,
    refetchInterval: 30_000,
  })

  const forensics = useQuery({
    queryKey: ['forensics-summary'],
    queryFn: forensicsApi.summary,
    refetchInterval: 30_000,
  })

  const findings = useQuery({
    queryKey: ['quality-findings', filter],
    queryFn: () =>
      auditApi.findings({ severity: filter === 'all' ? undefined : filter, limit: 100 }),
  })

  const quickWins = useQuery({
    queryKey: ['quality-quickwins'],
    queryFn: () => auditApi.quickWins(10),
    refetchInterval: 30_000,
  })

  const d = bundle.data
  const f = forensics.data

  const runAudit = async () => {
    setAction('audit')
    try {
      await auditApi.runAudit()
      await bundle.refetch()
      await forensics.refetch()
      await findings.refetch()
    } finally {
      setAction(null)
    }
  }

  const downloadDossier = () => {
    window.open('/api/forensics/dossier?format=markdown', '_blank')
  }

  const copyFixPrompt = (finding: QualityFinding) => {
    const prompt = `Please fix the following issue detected in ${finding.path}:${finding.line || 1}
Rule: ${finding.rule} (${finding.severity.toUpperCase()})
Title: ${finding.title}
Detail: ${finding.detail || 'None'}
Recommendation: ${finding.suggestion || 'Apply standard architectural best practice'}`
    navigator.clipboard.writeText(prompt)
    setCopiedId(finding.id)
    setTimeout(() => setCopiedId(null), 2000)
  }

  const jumpToLine = (path: string, line?: string | number) => {
    const ln = line ? `&line=${line}` : ''
    navigate(`/files?path=${encodeURIComponent(path)}${ln}`)
  }

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4">
        <div>
          <div className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[11px] font-mono text-accent bg-accent/10 border border-accent/20 mb-1">
            <Sparkles className="w-3 h-3" />
            <span>Forensic Intelligence Studio</span>
          </div>
          <h1 className="text-2xl font-semibold text-text-primary tracking-tight">Code Forensics & Quality</h1>
          <p className="text-text-muted text-sm">Deep architectural inspection, silent traps, ghost code & risk matrices.</p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={downloadDossier}
            className="flex items-center gap-1.5 rounded-lg border border-border bg-surface px-3 py-1.5 text-xs font-medium text-text-secondary hover:text-text-primary hover:border-border-subtle transition-colors cursor-pointer"
            title="Download Executive Dossier Report in Markdown"
          >
            <FileDown className="w-3.5 h-3.5 text-text-muted" />
            <span>Export Dossier</span>
          </button>
          <button
            onClick={runAudit}
            disabled={!!action}
            className="flex items-center gap-2 rounded-lg border border-accent/40 bg-accent/10 px-3.5 py-1.5 text-xs font-medium text-accent hover:bg-accent/20 transition-colors cursor-pointer disabled:opacity-50"
          >
            {action ? (
              <Loader2 className="w-3.5 h-3.5 animate-spin text-accent" />
            ) : (
              <RefreshCw className="w-3.5 h-3.5 text-accent" />
            )}
            Run Audit
          </button>
        </div>
      </div>

      {/* Forensic Navigation Tabs */}
      <div className="flex items-center gap-1 border-b border-border overflow-x-auto pb-px">
        <TabButton
          active={activeTab === 'overview'}
          onClick={() => setActiveTab('overview')}
          icon={Gauge}
          label="Health Overview"
          count={d?.health.overall_score ? `${Math.round(d.health.overall_score)}%` : undefined}
        />
        <TabButton
          active={activeTab === 'ghost'}
          onClick={() => setActiveTab('ghost')}
          icon={Ghost}
          label="Ghost Code & Buried Features"
          count={f?.dimensions.ghost_code.count}
          tone="accent"
        />
        <TabButton
          active={activeTab === 'silent'}
          onClick={() => setActiveTab('silent')}
          icon={ShieldAlert}
          label="Silent Traps"
          count={f?.dimensions.silent_traps.count}
          tone="error"
        />
        <TabButton
          active={activeTab === 'architecture'}
          onClick={() => setActiveTab('architecture')}
          icon={Layers}
          label="Architecture & Boundaries"
          count={f?.dimensions.architecture.count}
          tone="warning"
        />
        <TabButton
          active={activeTab === 'risk'}
          onClick={() => setActiveTab('risk')}
          icon={Flame}
          label="Risk Matrix & Hotspots"
          count={f?.dimensions.risk_matrix.hotspots?.length}
          tone="error"
        />
        <TabButton
          active={activeTab === 'secrets'}
          onClick={() => setActiveTab('secrets')}
          icon={KeyRound}
          label="Environment & Secrets"
          count={f?.dimensions.secrets_env.count}
          tone="warning"
        />
      </div>

      {/* Tab 1: Overview */}
      {activeTab === 'overview' && (
        <div className="space-y-6">
          <ScoreCard d={d} />

          {/* Summary chips */}
          <section className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <SummaryChip
              icon={AlertTriangle}
              label="Critical Issues"
              value={f?.by_severity.critical ?? d?.health.critical_issues}
              tone="error"
            />
            <SummaryChip
              icon={Zap}
              label="High Priority"
              value={f?.by_severity.high ?? d?.health.high_priority}
              tone="warning"
            />
            <SummaryChip
              icon={Ghost}
              label="Ghost Code Items"
              value={f?.dimensions.ghost_code.count}
              tone="accent"
            />
            <SummaryChip
              icon={HeartPulse}
              label="Total Findings"
              value={f?.total_findings ?? d?.findings.open}
              tone="muted"
            />
          </section>

          {/* All findings section */}
          <section className="space-y-3">
            <div className="flex items-center gap-2 flex-wrap">
              <h2 className="text-sm font-semibold text-text-primary mr-auto">Repository Findings</h2>
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
            <FindingsList
              findings={findings.data?.findings}
              onJump={jumpToLine}
              onCopyPrompt={copyFixPrompt}
              copiedId={copiedId}
            />
          </section>

          {/* Quick wins */}
          <section>
            <h2 className="text-sm font-semibold text-text-primary mb-3">Quick Wins & Low-Hanging Refactors</h2>
            <QuickWinsList wins={quickWins.data?.quick_wins} onJump={jumpToLine} />
          </section>
        </div>
      )}

      {/* Tab 2: Ghost Code & Buried Features */}
      {activeTab === 'ghost' && (
        <div className="space-y-4">
          <div className="rounded-lg border border-accent/20 bg-accent/5 p-4 text-xs text-text-secondary leading-relaxed">
            <p className="font-semibold text-accent mb-1 flex items-center gap-1.5">
              <Ghost className="w-4 h-4" /> Buried Capabilities & Dead Code Forensics
            </p>
            Unreferenced exports, hidden API routes, and unused database models represent either <strong>unexposed features ready to wire up</strong> or <strong>zombie assets ready to prune</strong>.
          </div>
          <FindingsList
            findings={f?.dimensions.ghost_code.findings}
            onJump={jumpToLine}
            onCopyPrompt={copyFixPrompt}
            copiedId={copiedId}
            emptyMessage="No ghost code or orphan exports detected. Repository is lean."
          />
        </div>
      )}

      {/* Tab 3: Silent Traps */}
      {activeTab === 'silent' && (
        <div className="space-y-4">
          <div className="rounded-lg border border-error/20 bg-error/5 p-4 text-xs text-text-secondary leading-relaxed">
            <p className="font-semibold text-error mb-1 flex items-center gap-1.5">
              <ShieldAlert className="w-4 h-4" /> Silent Traps & Error Swallowing Forensics
            </p>
            Silent exception catches (`except: pass`), unawaited database promises, and unvalidated Server Actions fail silently in production without generating alerts.
          </div>
          <FindingsList
            findings={f?.dimensions.silent_traps.findings}
            onJump={jumpToLine}
            onCopyPrompt={copyFixPrompt}
            copiedId={copiedId}
            emptyMessage="Zero silent exception swallows or unawaited queries detected."
          />
        </div>
      )}

      {/* Tab 4: Architecture & Boundaries */}
      {activeTab === 'architecture' && (
        <div className="space-y-4">
          <div className="rounded-lg border border-warning/20 bg-warning/5 p-4 text-xs text-text-secondary leading-relaxed">
            <p className="font-semibold text-warning mb-1 flex items-center gap-1.5">
              <Layers className="w-4 h-4" /> Architectural Boundary & Circular Dependency Forensics
            </p>
            Layer inversions (library packages importing UI components), monolithic god modules, and cyclic dependency loops discovered via <strong>Tarjan's Strongly Connected Components (SCC)</strong>.
          </div>

          {/* Tarjan Cycles if present */}
          {f?.dimensions.architecture.cycles && f.dimensions.architecture.cycles.length > 0 && (
            <div className="rounded-lg border border-border bg-surface p-4 space-y-2">
              <h3 className="text-xs font-semibold text-text-primary uppercase tracking-wider">
                Circular Dependency Cycles ({f.dimensions.architecture.cycles.length})
              </h3>
              <div className="space-y-2">
                {f.dimensions.architecture.cycles.map((c, i) => (
                  <div key={i} className="p-2.5 rounded bg-surface-raised border border-border-subtle text-xs font-mono text-warning">
                    <span className="text-text-muted mr-2">Cycle {i + 1} ({c.size} nodes):</span>
                    {c.symbols.join(' ➔ ')}
                  </div>
                ))}
              </div>
            </div>
          )}

          <FindingsList
            findings={f?.dimensions.architecture.findings}
            onJump={jumpToLine}
            onCopyPrompt={copyFixPrompt}
            copiedId={copiedId}
            emptyMessage="Zero architectural layer violations or circular dependencies found."
          />
        </div>
      )}

      {/* Tab 5: Risk Matrix & Hotspots */}
      {activeTab === 'risk' && (
        <div className="space-y-4">
          <div className="rounded-lg border border-error/20 bg-error/5 p-4 text-xs text-text-secondary leading-relaxed">
            <p className="font-semibold text-error mb-1 flex items-center gap-1.5">
              <Flame className="w-4 h-4" /> Blast Radius & Git Churn Risk Matrix
            </p>
            Correlation of <strong>time-decayed git commit frequency</strong> against <strong>unit test coverage deficits</strong>. Load-bearing files with high mutation and low coverage are high-risk failure points.
          </div>

          {/* Hotspots Grid */}
          {f?.dimensions.risk_matrix.hotspots && f.dimensions.risk_matrix.hotspots.length > 0 && (
            <div className="rounded-lg border border-border bg-surface overflow-hidden">
              <div className="px-4 py-3 border-b border-border flex items-center justify-between">
                <h3 className="text-xs font-semibold text-text-primary uppercase tracking-wider">
                  Top Risk Hotspots (Commit Frequency × Test Deficit)
                </h3>
              </div>
              <div className="divide-y divide-border-subtle">
                {f.dimensions.risk_matrix.hotspots.map((h) => (
                  <div key={h.path} className="p-3.5 flex items-center justify-between gap-4 hover:bg-surface-raised/40 transition-colors">
                    <div className="min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-xs text-text-primary truncate">{h.path}</span>
                        <span className={`px-1.5 py-0.5 rounded text-[9px] font-bold uppercase ${
                          h.risk_tier === 'critical' ? 'bg-red-500/20 text-red-400 border border-red-500/30' :
                          h.risk_tier === 'high' ? 'bg-orange-500/20 text-orange-400 border border-orange-500/30' :
                          'bg-zinc-500/20 text-zinc-400 border border-zinc-500/30'
                        }`}>
                          {h.risk_tier}
                        </span>
                      </div>
                      <p className="text-[11px] text-text-muted mt-0.5">
                        Churn score: <strong className="text-text-secondary font-mono">{h.churn_score}</strong> · Symbols: <span className="font-mono">{h.symbols_count}</span> · Test coverage: <strong className={h.coverage_pct < 50 ? 'text-amber-400 font-mono' : 'text-emerald-400 font-mono'}>{h.coverage_pct}%</strong>
                      </p>
                    </div>
                    <button
                      onClick={() => jumpToLine(h.path)}
                      className="px-2.5 py-1 rounded bg-surface-raised hover:bg-surface border border-border-subtle hover:border-accent text-text-muted hover:text-text-primary text-xs font-mono flex items-center gap-1 shrink-0 cursor-pointer"
                    >
                      <span>Inspect</span>
                      <ArrowRight className="w-3 h-3" />
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}

          <FindingsList
            findings={f?.dimensions.risk_matrix.findings}
            onJump={jumpToLine}
            onCopyPrompt={copyFixPrompt}
            copiedId={copiedId}
            emptyMessage="Zero untested load-bearing hot functions detected."
          />
        </div>
      )}

      {/* Tab 6: Environment & Secrets */}
      {activeTab === 'secrets' && (
        <div className="space-y-4">
          <div className="rounded-lg border border-warning/20 bg-warning/5 p-4 text-xs text-text-secondary leading-relaxed">
            <p className="font-semibold text-warning mb-1 flex items-center gap-1.5">
              <KeyRound className="w-4 h-4" /> Environment, Secret & Database Schema Integrity
            </p>
            Audit of environment variable discrepancies (used in code but absent from `.env`, or declared in `.env` but forgotten), database migration drift, and hardcoded credentials.
          </div>
          <FindingsList
            findings={f?.dimensions.secrets_env.findings}
            onJump={jumpToLine}
            onCopyPrompt={copyFixPrompt}
            copiedId={copiedId}
            emptyMessage="All environment variables, secrets, and database schemas are in sync."
          />
        </div>
      )}
    </div>
  )
}

function TabButton({
  active,
  onClick,
  icon: Icon,
  label,
  count,
  tone,
}: {
  active: boolean
  onClick: () => void
  icon: React.ComponentType<{ className?: string }>
  label: string
  count?: number | string
  tone?: 'error' | 'warning' | 'accent'
}) {
  const badgeColor = {
    error: 'bg-error/20 text-error',
    warning: 'bg-warning/20 text-warning',
    accent: 'bg-accent/20 text-accent',
  }[tone ?? 'accent']

  return (
    <button
      onClick={onClick}
      className={`flex items-center gap-2 px-3.5 py-2 text-xs font-medium border-b-2 transition-all whitespace-nowrap cursor-pointer ${
        active
          ? 'border-accent text-accent bg-accent/[0.04]'
          : 'border-transparent text-text-muted hover:text-text-primary hover:border-border'
      }`}
    >
      <Icon className="w-3.5 h-3.5" />
      <span>{label}</span>
      {count !== undefined && (
        <span className={`px-1.5 py-0.2 rounded-full text-[10px] font-mono font-medium ${badgeColor}`}>
          {count}
        </span>
      )}
    </button>
  )
}

function ScoreCard({ d }: { d?: QualityBundle }) {
  const score = d?.health.overall_score
  const parts = d?.breakdown
  if (!score || !parts) {
    return (
      <section className="rounded-lg border border-border bg-surface p-5 flex items-center gap-3">
        <Loader2 className="w-4 h-4 animate-spin text-accent" /> Loading health metrics…
      </section>
    )
  }
  const tone =
    score >= 80 ? 'text-success' : score >= 60 ? 'text-warning' : 'text-error'
  const r = 34
  const c = 2 * Math.PI * r
  const filled = (score / 100) * c
  return (
    <section className="rounded-xl border border-border bg-surface p-5 grid md:grid-cols-[auto_1fr] gap-6 items-center">
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
        <p className="text-xs text-text-muted uppercase tracking-wider font-semibold">Repository Health Score</p>
        <Bar label="Coverage" value={parts.coverage} />
        <Bar label="Quality" value={parts.quality} />
        <Bar label="Freshness" value={parts.freshness} />
        {parts.complexity !== null && parts.complexity !== undefined && (
          <Bar label="Complexity" value={parts.complexity} />
        )}
        {d && (
          <p className="text-[10px] font-mono text-text-muted">
            computed in {d.generated_ms}ms
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
    <div className="rounded-xl border border-border bg-surface p-4 flex items-center gap-3">
      <Icon className={`w-5 h-5 ${color}`} />
      <div>
        <p className="text-lg font-semibold font-mono text-text-primary">
          {value ?? '—'}
        </p>
        <p className="text-[10px] uppercase tracking-wider text-text-muted">{label}</p>
      </div>
    </div>
  )
}

function FindingsList({
  findings,
  onJump,
  onCopyPrompt,
  copiedId,
  emptyMessage = 'No findings in this category.',
}: {
  findings?: QualityFinding[]
  onJump: (path: string, line?: string | number) => void
  onCopyPrompt: (f: QualityFinding) => void
  copiedId: string | null
  emptyMessage?: string
}) {
  if (!findings) {
    return (
      <div className="rounded-xl border border-border bg-surface p-8 text-center text-xs text-text-muted flex items-center justify-center gap-2">
        <Loader2 className="w-4 h-4 animate-spin text-accent" /> Loading forensic findings…
      </div>
    )
  }

  if (findings.length === 0) {
    return (
      <div className="rounded-xl border border-border bg-surface p-8 text-center text-xs text-text-muted">
        {emptyMessage}
      </div>
    )
  }

  return (
    <div className="space-y-2.5">
      {findings.map((f) => (
        <div
          key={f.id}
          className="rounded-xl border border-border bg-surface p-4 hover:border-border-subtle transition-all space-y-2 group"
        >
          <div className="flex items-start justify-between gap-3">
            <div className="flex items-center gap-2 flex-wrap">
              <span className={`px-2 py-0.5 rounded text-[10px] font-semibold uppercase border ${SEVERITY_STYLE[f.severity]}`}>
                {f.severity}
              </span>
              <span className="font-mono text-xs font-medium text-accent bg-accent/10 px-2 py-0.5 rounded border border-accent/20">
                {f.rule}
              </span>
              <span className="font-mono text-xs text-text-muted">
                {f.path}{f.line ? `:${f.line}` : ''}
              </span>
            </div>
            <div className="flex items-center gap-1.5 shrink-0">
              <button
                onClick={() => onCopyPrompt(f)}
                className="flex items-center gap-1 px-2 py-1 rounded bg-surface-raised hover:bg-accent/10 text-text-muted hover:text-accent border border-border-subtle text-[11px] transition-colors cursor-pointer"
                title="Copy AI Prompt Pack for Claude/Gemini"
              >
                {copiedId === f.id ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                <span className="hidden sm:inline">{copiedId === f.id ? 'Copied' : 'AI Prompt'}</span>
              </button>
              <button
                onClick={() => onJump(f.path, f.line)}
                className="flex items-center gap-1 px-2.5 py-1 rounded bg-accent text-surface hover:bg-accent-light font-medium text-[11px] transition-colors cursor-pointer"
                title="Jump to line in Monaco editor"
              >
                <span>Jump</span>
                <ExternalLink className="w-3 h-3" />
              </button>
            </div>
          </div>

          <p className="text-xs font-medium text-text-primary leading-snug">{f.title}</p>
          {f.detail && <p className="text-[11px] text-text-muted font-mono bg-surface-raised p-2 rounded border border-border-subtle">{f.detail}</p>}
          {f.suggestion && (
            <p className="text-[11px] text-emerald-400/90 leading-relaxed bg-emerald-500/5 border border-emerald-500/10 p-2 rounded">
              💡 <strong>Action:</strong> {f.suggestion}
            </p>
          )}
        </div>
      ))}
    </div>
  )
}

function QuickWinsList({
  wins,
  onJump,
}: {
  wins?: QualityBundle['quick_wins']
  onJump: (path: string, line?: string | number) => void
}) {
  if (!wins) return <p className="text-xs text-text-muted">Loading quick wins…</p>
  if (wins.length === 0) return <p className="text-xs text-text-muted">No quick wins available.</p>
  return (
    <div className="grid sm:grid-cols-2 gap-3">
      {wins.map((w) => (
        <div
          key={w.id}
          className="rounded-xl border border-border bg-surface p-3.5 flex flex-col justify-between gap-2 hover:border-border-subtle transition-all"
        >
          <div className="space-y-1">
            <div className="flex items-center justify-between">
              <span className={`px-1.5 py-0.5 rounded text-[9px] font-semibold uppercase border ${SEVERITY_STYLE[w.severity]}`}>
                {w.effort} effort
              </span>
              <span className="text-[10px] font-mono text-accent">{w.rule}</span>
            </div>
            <p className="text-xs font-medium text-text-primary leading-snug">{w.title}</p>
            <p className="text-[10px] text-text-muted line-clamp-2">{w.suggestion}</p>
          </div>
          <div className="flex items-center justify-between pt-2 border-t border-border-subtle">
            <span className="text-[10px] font-mono text-text-muted truncate max-w-[180px]">{w.path}</span>
            <button
              onClick={() => onJump(w.path, w.line)}
              className="text-[10px] font-medium text-accent hover:underline flex items-center gap-0.5 cursor-pointer"
            >
              <span>Inspect</span>
              <ArrowRight className="w-2.5 h-2.5" />
            </button>
          </div>
        </div>
      ))}
    </div>
  )
}