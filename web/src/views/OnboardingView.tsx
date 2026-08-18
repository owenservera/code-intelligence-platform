import { useEffect, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  Rocket,
  FolderTree,
  SlidersHorizontal,
  Database,
  CheckCircle2,
  Loader2,
  ArrowRight,
  ArrowLeft,
  Languages,
  GitBranch,
  PackageOpen,
  AlertTriangle,
  RefreshCw,
  ShieldCheck,
} from 'lucide-react'
import { indexApi, settingsApi, type OnboardingState } from '@/lib/api'

const STEPS = ['Repo', 'Config review', 'Index & verify', 'Done']

export function OnboardingView({
  status,
  onSkip,
  onIndexed,
}: {
  status: OnboardingState
  onSkip: () => void
  onIndexed: () => void
}) {
  const [step, setStep] = useState(status.status === 'initialized_no_index' ? 2 : 0)
  const [syncing, setSyncing] = useState(false)

  const admission = useQuery({
    queryKey: ['admission'],
    queryFn: indexApi.admission,
    enabled: step === 2,
  })
  const config = useQuery({
    queryKey: ['config-bundle'],
    queryFn: settingsApi.bundle,
    enabled: step === 1,
  })

  // Poll index status while syncing so the gate flips the moment it lands.
  const index = useQuery({
    queryKey: ['index-status'],
    queryFn: indexApi.status,
    enabled: syncing,
    refetchInterval: syncing ? 3_000 : 5_000,
  })

  const startSync = async () => {
    setSyncing(true)
    setStep(2)
    try {
      await indexApi.sync(false)
    } catch (e) {
      setSyncing(false)
      alert(`Sync failed: ${String(e)}`)
    }
  }

  useEffect(() => {
    if (syncing && index.data && (index.data as { files?: number }).files) {
      setSyncing(false)
      onIndexed()
    }
  }, [syncing, index.data, onIndexed])

  const d = status.detection
  const recommendations = status.recommendations ?? []

  return (
    <div className="min-h-screen bg-bg flex items-start justify-center py-12 px-4">
      <div className="w-full max-w-2xl space-y-6">
        {/* Header */}
        <div className="text-center">
          <div className="inline-flex items-center gap-2 text-accent mb-2">
            <Rocket className="w-5 h-5" />
            <span className="text-sm font-semibold tracking-wide">CIP Repo Activation</span>
          </div>
          <h1 className="text-2xl font-semibold text-text-primary">
            {status.status_label}
          </h1>
          <p className="text-text-muted text-sm mt-1">
            Get this repo indexed and live in a few steps.
          </p>
        </div>

        {/* Stepper */}
        <div className="flex items-center justify-center gap-1">
          {STEPS.map((label, i) => (
            <div key={label} className="flex items-center gap-1">
              <div
                className={`flex items-center gap-1.5 px-2 py-1 rounded-md text-[11px] ${
                  i < step
                    ? 'text-success'
                    : i === step
                      ? 'bg-accent/15 text-accent font-medium'
                      : 'text-text-muted'
                }`}
              >
                <span className="font-mono">{i < step ? <CheckCircle2 className="w-3.5 h-3.5" /> : i + 1}</span>
                {label}
              </div>
              {i < STEPS.length - 1 && <span className="text-border-subtle mx-0.5">→</span>}
            </div>
          ))}
        </div>

        {/* ERROR card */}
        {status.status === 'error' && (
          <div className="rounded-lg border border-error/40 bg-error/10 p-4 text-sm">
            <p className="flex items-center gap-2 text-error font-medium">
              <AlertTriangle className="w-4 h-4" /> Detection failed
            </p>
            <p className="text-text-muted mt-1 font-mono text-xs">{status.error_message}</p>
            {recommendations.map((r) => (
              <p key={r} className="text-text-muted text-xs mt-1">• {r}</p>
            ))}
          </div>
        )}

        {/* Step 0 — Repo intro */}
        {step === 0 && (
          <section className="rounded-lg border border-border bg-surface p-6 space-y-4">
            <div className="flex items-center gap-2">
              <FolderTree className="w-4 h-4 text-accent" />
              <h2 className="text-sm font-medium text-text-primary">Your repository</h2>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <InfoCard icon={PackageOpen} label="Repo type" value={d?.repo_type ?? '—'} />
              <InfoCard icon={GitBranch} label="Git" value={d?.has_git ? (d.git_branch ?? 'tracked') : 'none'} />
              <InfoCard icon={Languages} label="Languages" value={(d?.languages ?? []).join(', ') || '—'} />
              <InfoCard icon={Database} label="Files found" value={String(d?.file_count ?? '—')} />
            </div>
            {d?.has_git && d.git_uncommitted > 0 && (
              <p className="text-xs text-warning">{d.git_uncommitted} uncommitted file(s).</p>
            )}
            <RecList title="Recommended next" items={recommendations} />
            <div className="flex justify-end">
              <Btn onClick={() => setStep(1)}>
                Review suggested config <ArrowRight className="w-3.5 h-3.5" />
              </Btn>
            </div>
          </section>
        )}

        {/* Step 1 — Config review */}
        {step === 1 && (
          <section className="rounded-lg border border-border bg-surface p-6 space-y-4">
            <div className="flex items-center gap-2">
              <SlidersHorizontal className="w-4 h-4 text-accent" />
              <h2 className="text-sm font-medium text-text-primary">Suggested configuration</h2>
              <span className="ml-auto text-[10px] text-text-muted">
                auto-detected — fully editable in Settings
              </span>
            </div>
            {!config.data ? (
              <p className="text-xs text-text-muted">Loading effective config…</p>
            ) : (
              <EffectiveConfig eff={config.data.effective} />
            )}
            {d && d.languages.length > 0 && (
              <p className="text-xs text-text-muted">
                Chosen from detected <span className="font-mono">{d.repo_type}</span> profile + repo evidence.
              </p>
            )}
            <div className="flex justify-between">
              <Btn variant="ghost" onClick={() => setStep(0)}>
                <ArrowLeft className="w-3.5 h-3.5" /> Back
              </Btn>
              <Btn onClick={startSync}>
                {syncing ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Database className="w-3.5 h-3.5" />}
                Index repository
              </Btn>
            </div>
          </section>
        )}

        {/* Step 2 — Index & verify */}
        {step === 2 && (
          <section className="rounded-lg border border-border bg-surface p-6 space-y-4">
            <div className="flex items-center gap-2">
              <Database className="w-4 h-4 text-accent" />
              <h2 className="text-sm font-medium text-text-primary">Index & verify</h2>
              <span className="ml-auto flex items-center gap-1.5 text-[11px] text-text-muted">
                {syncing ? (
                  <>
                    <Loader2 className="w-3.5 h-3.5 animate-spin text-accent" /> building…
                  </>
                ) : (
                  <span className="text-success">complete</span>
                )}
              </span>
            </div>

            {!syncing && index.data ? (
              <IndexSummary files={(index.data as { files?: number }).files} admission={admission.data} />
            ) : (
              <div className="space-y-2">
                <div className="rounded-md bg-surface-raised border border-border-subtle p-3 text-xs text-text-muted">
                  <ShieldCheck className="w-3.5 h-3.5 inline-block mr-1.5 text-success" />
                  Running incremental sync as a background job. The console unlocks the moment the
                  first files are indexed.
                </div>
                {!syncing && (
                  <div className="flex justify-end">
                    <Btn onClick={() => startSync()}>
                      <RefreshCw className="w-3.5 h-3.5" /> Re-run sync
                    </Btn>
                  </div>
                )}
              </div>
            )}
            {!syncing && (
              <div className="flex justify-between">
                <Btn variant="ghost" onClick={() => setStep(1)}>
                  <ArrowLeft className="w-3.5 h-3.5" /> Back
                </Btn>
                <Btn variant="ghost" onClick={onIndexed} disabled={!(index.data as { files?: number })?.files}>
                  Land on Command Center <ArrowRight className="w-3.5 h-3.5" />
                </Btn>
              </div>
            )}
          </section>
        )}

        <div className="text-center">
          <button
            onClick={onSkip}
            className="text-xs text-text-muted hover:text-text-secondary underline underline-offset-2 cursor-pointer"
          >
            Skip for now
          </button>
        </div>
      </div>
    </div>
  )
}

function InfoCard({ icon: Icon, label, value }: { icon: React.ComponentType<{ className?: string }>; label: string; value: string }) {
  return (
    <div className="rounded-md border border-border-subtle bg-surface-raised p-3">
      <p className="flex items-center gap-1.5 text-[10px] uppercase tracking-wider text-text-muted">
        <Icon className="w-3 h-3" /> {label}
      </p>
      <p className="text-sm font-mono text-text-primary mt-1 truncate">{value}</p>
    </div>
  )
}

function RecList({ title, items }: { title: string; items: string[] }) {
  if (!items.length) return null
  return (
    <div className="space-y-1">
      <p className="text-[10px] uppercase tracking-wider text-text-muted">{title}</p>
      {items.map((r) => (
        <p key={r} className="text-xs text-text-secondary">• {r}</p>
      ))}
    </div>
  )
}

function EffectiveConfig({ eff }: { eff: Record<string, Record<string, unknown>> }) {
  const index = eff.index ?? {}
  const embed = eff.embed ?? {}
  const summary = eff.summary ?? {}
  const git = eff.git ?? {}
  return (
    <div className="space-y-2 text-xs">
      <KV k="index.max_file_kb" v={String(index.max_file_kb ?? '—')} note="file size cap" />
      <KV k="index.include" v={fmtArr(index.include)} note="restricted paths (empty = whole repo)" />
      <KV k="index.exclude" v={fmtArr(index.exclude)} note="hard defaults always apply" />
      <KV k="embed.backend" v={String(embed.backend ?? 'auto')} note="no model loads until daemon warms" />
      <KV k="summary.backend" v={String(summary.backend ?? 'structural')} />
      <KV k="git.depth" v={String(git.depth ?? '500')} />
    </div>
  )
}

function KV({ k, v, note }: { k: string; v: string; note?: string }) {
  return (
    <div className="flex items-start gap-2 rounded-md border border-border-subtle bg-surface-raised px-3 py-2">
      <span className="font-mono text-accent whitespace-pre">{k}</span>
      <span className="font-mono text-text-primary ml-auto text-right break-all">{v}</span>
      {note && <span className="text-text-muted text-[10px] basis-1/3 text-right">{note}</span>}
    </div>
  )
}

function IndexSummary({
  files,
  admission,
}: {
  files?: number
  admission?: { mode?: string; index_tiers?: Record<string, number> }
}) {
  const tiers = admission?.index_tiers ?? {}
  return (
    <div className="rounded-md border border-success/30 bg-success/5 p-4 text-xs text-text-secondary space-y-2">
      <p className="flex items-center gap-1.5 font-medium text-success">
        <CheckCircle2 className="w-4 h-4" /> Index live — {files ?? 0} files indexed
      </p>
      {admission && (
        <p className="text-text-muted">
          admission mode: <span className="font-mono text-text-primary">{admission.mode ?? '—'}</span>
          {Object.entries(tiers).map(([t, n]) => (
            <span key={t} className="ml-2">
              {t}: <span className="font-mono text-success">{n}</span>
            </span>
          ))}
        </p>
      )}
    </div>
  )
}

function fmtArr(v: unknown): string {
  if (Array.isArray(v) && v.length) return v.join(', ')
  return '—'
}

function Btn({
  children,
  onClick,
  variant = 'primary',
  disabled,
}: {
  children: React.ReactNode
  onClick: () => void
  variant?: 'primary' | 'ghost'
  disabled?: boolean
}) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className={`inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-md text-xs font-medium cursor-pointer transition-colors disabled:opacity-50 ${
        variant === 'primary'
          ? 'bg-accent text-bg hover:opacity-90'
          : 'text-text-secondary hover:text-text-primary border border-border-subtle hover:border-border'
      }`}
    >
      {children}
    </button>
  )
}