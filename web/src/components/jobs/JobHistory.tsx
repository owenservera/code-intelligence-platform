import { useEffect } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { jobApi, type JobInfo } from '@/lib/api'
import { useJobsStore } from '@/stores/jobs'
import { RotateCcw, Square } from 'lucide-react'

const STATUS_TONE: Record<JobInfo['status'], string> = {
  running: 'text-accent',
  done: 'text-success',
  error: 'text-error',
  cancelled: 'text-text-muted',
}

export function JobHistory() {
  const jobs = useJobsStore((s) => s.jobs)
  const order = useJobsStore((s) => s.order)
  const seed = useJobsStore((s) => s.seed)
  const qc = useQueryClient()

  const q = useQuery({ queryKey: ['jobs'], queryFn: () => jobApi.list(30) })
  useEffect(() => {
    if (q.data) seed(q.data.jobs)
  }, [q.data, seed])

  const rows = order.map((id) => jobs[id]).filter(Boolean).slice(0, 30)
  if (rows.length === 0) {
    return <p className="text-xs text-text-muted py-4">No jobs yet.</p>
  }

  const rerun = (j: JobInfo) => {
    void jobApi
      .run(j.command, j.params ?? {})
      .then(() => qc.invalidateQueries({ queryKey: ['jobs'] }))
  }

  return (
    <div className="rounded-lg border border-border bg-surface overflow-hidden">
      <table className="w-full text-left text-xs">
        <thead className="bg-surface-raised text-[10px] uppercase tracking-wider text-text-muted">
          <tr>
            <th className="px-3 py-2">Command</th>
            <th className="px-3 py-2">Status</th>
            <th className="px-3 py-2">Duration</th>
            <th className="px-3 py-2">Summary</th>
            <th className="px-3 py-2" />
          </tr>
        </thead>
        <tbody className="divide-y divide-border-subtle">
          {rows.map((j) => (
            <tr key={j.id} className="hover:bg-surface-raised/40 transition-colors">
              <td className="px-3 py-2 font-mono text-text-primary">{j.command}</td>
              <td className={`px-3 py-2 ${STATUS_TONE[j.status]}`}>{j.status}</td>
              <td className="px-3 py-2 font-mono text-text-muted">
                {j.finished ? `${Math.round(j.finished - j.started)}s` : '—'}
              </td>
              <td className="px-3 py-2 text-text-muted max-w-[24ch] truncate">
                {j.error ??
                  (j.result ? JSON.stringify(j.result).slice(0, 48) : j.phase ?? '')}
              </td>
              <td className="px-3 py-2 flex gap-1 justify-end">
                {j.status === 'running' && (
                  <button
                    onClick={() => jobApi.cancel(j.id).catch(() => {})}
                    className="p-1 rounded text-text-muted hover:text-error transition-colors cursor-pointer"
                    title="Cancel"
                  >
                    <Square className="w-3.5 h-3.5" />
                  </button>
                )}
                {j.status !== 'running' && (
                  <button
                    onClick={() => rerun(j)}
                    className="p-1 rounded text-text-muted hover:text-accent transition-colors cursor-pointer"
                    title="Re-run"
                  >
                    <RotateCcw className="w-3.5 h-3.5" />
                  </button>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
