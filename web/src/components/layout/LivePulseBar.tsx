import { useAppStore } from '@/stores/app'
import { Activity, Cpu, Sparkles } from 'lucide-react'

export function LivePulseBar({ onOpenContextPack }: { onOpenContextPack?: () => void }) {
  const status = useAppStore((s) => s.status)
  const activeProject = useAppStore((s) => s.activeProject)
  const projects = useAppStore((s) => s.projects)

  const active = projects.find((p) => p.id === activeProject)
  const isWsConnected = status.connection === 'ok'
  const isDaemonRunning = !!status.daemonPid

  return (
    <footer className="h-7 border-t border-border bg-surface flex items-center justify-between px-3 text-[11px] font-mono text-text-muted shrink-0 select-none">
      {/* Left: WS Pulse & Daemon State */}
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-1.5" title={isWsConnected ? 'WebSocket live event telemetry connected' : 'Connecting to WebSocket...'}>
          <span className={`w-2 h-2 rounded-full ${isWsConnected ? 'bg-emerald-400 animate-pulse' : 'bg-amber-400'}`} />
          <span className="text-[10px] uppercase font-semibold text-text-secondary">{isWsConnected ? 'LIVE' : 'SYNCING'}</span>
        </div>

        <span className="text-border-subtle">|</span>

        <div className="flex items-center gap-1.5">
          <Activity className="w-3 h-3 text-accent" />
          <span>Daemon:</span>
          <span className={isDaemonRunning ? 'text-emerald-400 font-semibold' : 'text-text-muted'}>
            {isDaemonRunning ? `online (${status.daemonPid})` : 'idle'}
          </span>
        </div>

        {active?.repo_type && (
          <>
            <span className="text-border-subtle hidden sm:inline">|</span>
            <div className="hidden sm:flex items-center gap-1 text-emerald-400/90">
              <span>profile:</span>
              <strong className="text-emerald-300">{active.repo_type}</strong>
            </div>
          </>
        )}
      </div>

      {/* Right: Anti-compaction Token Budget Indicator & Context Pack Launcher */}
      <div className="flex items-center gap-3">
        <div className="hidden md:flex items-center gap-1.5 text-text-muted text-[10px]">
          <Cpu className="w-3 h-3 text-accent" />
          <span>120K Token Ceiling:</span>
          <span className="text-emerald-400 font-semibold">Healthy (Tier 0)</span>
        </div>

        {onOpenContextPack && (
          <button
            onClick={onOpenContextPack}
            className="flex items-center gap-1 px-2 py-0.5 rounded bg-accent/10 hover:bg-accent/20 text-accent text-[10px] font-medium transition-colors cursor-pointer border border-accent/20"
            title="Generate Token-budgeted Context Pack for AI Prompting"
          >
            <Sparkles className="w-3 h-3" />
            <span>AI Context Pack</span>
          </button>
        )}
      </div>
    </footer>
  )
}

