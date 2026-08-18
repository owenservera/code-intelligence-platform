import { Wifi, WifiOff, Server, Database, Cpu } from 'lucide-react'
import { useAppStore } from '@/stores/app'

export function StatusBar() {
  const status = useAppStore((s) => s.status)

  return (
    <footer className="h-7 border-t border-border bg-surface flex items-center px-3 gap-4 text-[11px] font-mono text-text-muted shrink-0">
      <StatusChip
        icon={status.connection === 'ok' ? Wifi : WifiOff}
        label="WS"
        level={status.connection}
      />
      <StatusChip
        icon={Server}
        label={status.daemonPid ? `daemon ${status.daemonPid}` : 'daemon off'}
        level={status.daemon}
      />
      <StatusChip
        icon={Database}
        label={status.indexAge ? `indexed ${status.indexAge}` : 'no index'}
        level={status.index}
      />
      <StatusChip
        icon={Cpu}
        label={status.embedderBackend ?? 'embedder'}
        level={status.embedder}
      />
      <div className="flex-1" />
      <span className="text-text-muted/50">CIP v2.1</span>
    </footer>
  )
}

function StatusChip({
  icon: Icon,
  label,
  level,
}: {
  icon: React.ComponentType<{ className?: string }>
  label: string
  level: string
}) {
  const color = {
    ok: 'text-success',
    warn: 'text-warning',
    error: 'text-error',
    loading: 'text-zinc-500',
  }[level] ?? 'text-zinc-500'

  return (
    <span className={`flex items-center gap-1 ${color}`}>
      <Icon className="w-3 h-3" />
      {label}
    </span>
  )
}
