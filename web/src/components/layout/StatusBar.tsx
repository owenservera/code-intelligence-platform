import { useState } from 'react'
import { Wifi, WifiOff, Server, Database, Cpu, Sparkles, ShieldCheck } from 'lucide-react'
import { useAppStore } from '@/stores/app'
import { ContextPackModal } from '../ai/ContextPackModal'

export function StatusBar() {
  const status = useAppStore((s) => s.status)
  const activeProject = useAppStore((s) => s.activeProject)
  const projects = useAppStore((s) => s.projects)
  const [contextPackOpen, setContextPackOpen] = useState(false)

  const active = projects.find((p) => p.id === activeProject)

  return (
    <>
      <footer className="h-7 border-t border-border bg-surface flex items-center px-3 gap-4 text-[11px] font-mono text-text-muted shrink-0 select-none">
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

        {active?.repo_type && (
          <div className="hidden sm:flex items-center gap-1 text-emerald-400">
            <span>profile:</span>
            <strong className="text-emerald-300 font-medium">{active.repo_type}</strong>
          </div>
        )}

        <div className="flex-1" />

        {/* 120K Canonical Anti-Compaction Context Gauge */}
        <div className="hidden md:flex items-center gap-1.5 text-text-muted text-[10px]">
          <ShieldCheck className="w-3 h-3 text-emerald-400" />
          <span>120K Ceiling:</span>
          <span className="text-emerald-400 font-semibold">Tier 0 (Safe)</span>
        </div>

        <button
          onClick={() => setContextPackOpen(true)}
          className="flex items-center gap-1 px-2 py-0.5 rounded bg-accent/10 hover:bg-accent/20 text-accent text-[10px] font-medium transition-colors cursor-pointer border border-accent/20"
          title="Open AI Context Pack Studio"
        >
          <Sparkles className="w-2.5 h-2.5" />
          <span>AI Context</span>
        </button>

        <span className="text-text-muted/50 hidden sm:inline">CIP v2.1</span>
      </footer>

      <ContextPackModal
        isOpen={contextPackOpen}
        onClose={() => setContextPackOpen(false)}
      />
    </>
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

