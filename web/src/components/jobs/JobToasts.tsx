import { useEffect, useState } from 'react'
import { Loader2, X, CheckCircle2, XCircle, Ban } from 'lucide-react'
import { useJobsStore } from '@/stores/jobs'
import { jobApi } from '@/lib/api'
import type { JobInfo } from '@/lib/api'

function Toast({ job, onDismiss }: { job: JobInfo; onDismiss: (id: string) => void }) {
  const [gone, setGone] = useState(false)
  const terminal = job.status === 'done' || job.status === 'error' || job.status === 'cancelled'

  // Auto-dismiss terminal jobs after 5s.
  useEffect(() => {
    if (terminal) {
      const t = setTimeout(() => setGone(true), 5000)
      return () => clearTimeout(t)
    }
  }, [terminal])

  if (gone) return null

  const icon =
    job.status === 'done' ? (
      <CheckCircle2 className="w-4 h-4 text-success shrink-0" />
    ) : job.status === 'error' ? (
      <XCircle className="w-4 h-4 text-error shrink-0" />
    ) : job.status === 'cancelled' ? (
      <Ban className="w-4 h-4 text-warning shrink-0" />
    ) : (
      <Loader2 className="w-4 h-4 text-accent animate-spin shrink-0" />
    )

  return (
    <div className="w-80 rounded-xl border border-border bg-surface shadow-lg overflow-hidden">
      <div className="flex items-center gap-2 px-3 py-2">
        {icon}
        <span className="flex-1 truncate font-mono text-xs text-text-primary">{job.command}</span>
        <button
          onClick={() => onDismiss(job.id)}
          className="text-text-muted hover:text-text-primary transition-colors cursor-pointer"
          aria-label="Dismiss"
        >
          <X className="w-3.5 h-3.5" />
        </button>
      </div>
      {job.status === 'running' && (
        <div className="px-3 pb-2 space-y-1">
          <div className="h-1.5 rounded-full bg-bg overflow-hidden">
            <div
              className="h-full bg-accent transition-all"
              style={{ width: `${Math.min(job.pct ?? 0, 100)}%` }}
            />
          </div>
          <div className="flex items-center justify-between gap-2">
            <span className="flex-1 truncate text-[10px] font-mono text-text-muted">
              {job.phase ?? 'working…'}
            </span>
            <span className="text-[10px] font-mono text-text-muted">{Math.min(job.pct ?? 0, 100)}%</span>
          </div>
          <button
            onClick={() => jobApi.cancel(job.id).catch(() => {})}
            className="rounded-md border border-border-subtle bg-bg px-2 py-0.5 text-[10px] font-medium text-text-muted hover:text-error hover:border-error/50 transition-colors cursor-pointer"
          >
            Cancel
          </button>
        </div>
      )}
    </div>
  )
}

export function JobToasts() {
  const jobs = useJobsStore((s) => s.jobs)
  const order = useJobsStore((s) => s.order)
  const [dismissed, setDismissed] = useState<Record<string, boolean>>({})

  const active = order.map((id) => jobs[id]).filter(Boolean)
  const running = active.filter((j) => j.status === 'running').slice(-3)
  const recent = active
    .filter((j) => j.status !== 'running' && !dismissed[j.id])
    .slice(-2)

  const toasts = [...running, ...recent].filter((j) => !dismissed[j.id]).slice(-5)
  const dismiss = (id: string) => setDismissed((d) => ({ ...d, [id]: true }))

  if (toasts.length === 0) return null
  return (
    <div className="fixed bottom-10 right-4 z-50 flex flex-col gap-2">
      {toasts.map((j) => (
        <Toast key={j.id} job={j} onDismiss={dismiss} />
      ))}
    </div>
  )
}
