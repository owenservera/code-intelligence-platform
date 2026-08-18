import { useAppStore } from '@/stores/app'
import { JobHistory } from '@/components/jobs/JobHistory'
import { Server, Database, Cpu, Search, Terminal, BarChart3 } from 'lucide-react'

const QUICK_ACTIONS = [
  { label: 'Sync Index', icon: Database, command: 'sync', color: 'text-accent' },
  { label: 'Search Code', icon: Search, command: 'search', color: 'text-success' },
  { label: 'Run Audit', icon: BarChart3, command: 'audit', color: 'text-warning' },
  { label: 'Daemon Status', icon: Server, command: 'daemon status', color: 'text-accent' },
  { label: 'Self Test', icon: Terminal, command: 'selftest', color: 'text-text-secondary' },
  { label: 'Health Check', icon: Cpu, command: 'doctor', color: 'text-success' },
]

export function CommandCenter() {
  const setCommandPaletteOpen = useAppStore((s) => s.setCommandPaletteOpen)
  const status = useAppStore((s) => s.status)

  return (
    <div className="max-w-4xl mx-auto space-y-8">
      <div>
        <h1 className="text-2xl font-semibold text-text-primary mb-1">Command Center</h1>
        <p className="text-text-muted text-sm">
          Central hub for CIP operations. Use{' '}
          <kbd className="px-1.5 py-0.5 rounded bg-surface-raised border border-border-subtle text-[11px] font-mono">
            Ctrl+K
          </kbd>{' '}
          to open the command palette.
        </p>
      </div>

      {/* Status Overview */}
      <div className="grid grid-cols-4 gap-3">
        <StatusCard title="Connection" level={status.connection} detail={status.connection === 'ok' ? 'WebSocket live' : 'Disconnected'} />
        <StatusCard title="Daemon" level={status.daemon} detail={status.daemonPid ? `PID ${status.daemonPid}` : 'Not running'} />
        <StatusCard title="Index" level={status.index} detail={status.indexAge ?? 'No index'} />
        <StatusCard title="Embedder" level={status.embedder} detail={status.embedderBackend ?? 'Unknown'} />
      </div>

      {/* Quick Actions */}
      <div>
        <h2 className="text-sm font-medium text-text-secondary mb-3">Quick Actions</h2>
        <div className="grid grid-cols-3 gap-2">
          {QUICK_ACTIONS.map(({ label, icon: Icon, command, color }) => (
            <button
              key={command}
              onClick={() => setCommandPaletteOpen(true)}
              className="flex items-center gap-2.5 px-4 py-3 rounded-lg bg-surface border border-border-subtle
                         hover:border-border hover:bg-surface-raised transition-colors text-left cursor-pointer group"
            >
              <Icon className={`w-4 h-4 ${color} group-hover:scale-110 transition-transform`} />
              <span className="text-sm text-text-primary">{label}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Recent Jobs */}
      <div>
        <h2 className="text-sm font-medium text-text-secondary mb-3">Recent Jobs</h2>
        <JobHistory />
      </div>

      {/* Getting Started hint */}
      {status.connection !== 'ok' && (
        <div className="p-4 rounded-lg bg-warning/10 border border-warning/30 text-warning text-sm">
          WebSocket not connected. Start the CIP daemon: <code className="font-mono">cip daemon start</code>
        </div>
      )}
    </div>
  )
}

function StatusCard({ title, level, detail }: { title: string; level: string; detail: string }) {
  const color = {
    ok: 'border-success/30 bg-success/5',
    warn: 'border-warning/30 bg-warning/5',
    error: 'border-error/30 bg-error/5',
    loading: 'border-zinc-700 bg-zinc-900',
  }[level] ?? 'border-zinc-700 bg-zinc-900'

  const dot = {
    ok: 'bg-success',
    warn: 'bg-warning',
    error: 'bg-error',
    loading: 'bg-zinc-500 animate-pulse',
  }[level] ?? 'bg-zinc-500'

  return (
    <div className={`rounded-lg border p-3 ${color}`}>
      <div className="flex items-center gap-2 mb-1">
        <div className={`w-1.5 h-1.5 rounded-full ${dot}`} />
        <span className="text-xs font-medium text-text-secondary">{title}</span>
      </div>
      <p className="text-xs text-text-muted font-mono">{detail}</p>
    </div>
  )
}
