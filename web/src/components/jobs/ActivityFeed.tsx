import { useEventsStore } from '@/stores/events'

const TYPE_TONE: Record<string, string> = {
  'watch.event': 'text-warning',
  'index.update': 'text-accent',
  'quality.update': 'text-success',
  'memory.updated': 'text-success',
  'config.update': 'text-text-muted',
  'signals.ingested': 'text-text-muted',
  'workflow.step': 'text-accent',
}

function ago(ts: number): string {
  const s = Math.max(0, Math.round(Date.now() / 1000 - ts))
  if (s < 60) return `${s}s ago`
  return `${Math.round(s / 60)}m ago`
}

export function ActivityFeed() {
  const lines = useEventsStore((s) => s.lines)
  if (lines.length === 0) return null
  return (
    <div className="rounded-lg border border-border bg-surface p-3 space-y-1">
      <h3 className="text-[10px] uppercase tracking-wider text-text-muted mb-1">Live Activity</h3>
      {lines.slice(-6).reverse().map((l) => (
        <div key={l.id} className="flex items-center gap-2 text-[11px] font-mono">
          <span className="text-text-muted shrink-0">{ago(l.ts)}</span>
          <span className={`shrink-0 ${TYPE_TONE[l.type] ?? 'text-text-muted'}`}>{l.type}</span>
          <span className="text-text-secondary truncate">{l.command ?? ''}</span>
          <span className="text-text-muted truncate">{l.message}</span>
        </div>
      ))}
    </div>
  )
}
