import { useState } from 'react'
import { Search, Terminal, Command, ChevronsUpDown, Plus, Sparkles } from 'lucide-react'
import { Link, useNavigate } from 'react-router-dom'
import { useAppStore } from '@/stores/app'
import { ContextPackModal } from '../ai/ContextPackModal'

export function TopBar() {
  const setCommandPaletteOpen = useAppStore((s) => s.setCommandPaletteOpen)
  const status = useAppStore((s) => s.status)
  const activeProject = useAppStore((s) => s.activeProject)
  const projects = useAppStore((s) => s.projects)
  const setActiveProject = useAppStore((s) => s.setActiveProject)
  const [contextPackOpen, setContextPackOpen] = useState(false)
  const navigate = useNavigate()

  const active = projects.find((p) => p.id === activeProject)

  return (
    <>
      <header className="h-12 border-b border-border flex items-center px-4 gap-3 shrink-0 bg-surface">
        <div className="flex items-center gap-2">
          <Terminal className="w-4 h-4 text-accent" />
          <span className="font-semibold text-sm text-text-primary tracking-tight">CIP Console</span>
        </div>

        {/* SPEC-19 §3: project switcher — switch re-scopes every API call + WS (PLAN-06 T6.3). */}
        {projects.length > 0 ? (
          <div className="flex items-center gap-2">
            <div className="relative flex items-center">
              <select
                value={activeProject ?? ''}
                onChange={(e) => {
                  setActiveProject(e.target.value || null)
                  navigate('/')
                }}
                className="appearance-none pl-3 pr-8 py-1.5 rounded-md bg-surface-raised border border-border-subtle
                           text-xs text-text-primary hover:border-border cursor-pointer max-w-56 truncate"
                aria-label="Active project"
              >
                {projects.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name}
                  </option>
                ))}
              </select>
              <ChevronsUpDown className="w-3 h-3 text-text-muted pointer-events-none absolute right-2.5" />
            </div>
            {active?.repo_type && (
              <span className="hidden sm:inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-mono text-emerald-400 bg-emerald-500/10 border border-emerald-500/20" title={`Active repo profile: ${active.repo_type}`}>
                profile: {active.repo_type}
              </span>
            )}
          </div>
        ) : (
          <Link
            to="/projects"
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-surface-raised border border-border-subtle
                       hover:border-accent text-text-muted hover:text-text-primary text-xs cursor-pointer"
          >
            <Plus className="w-3 h-3" />
            <span>Add project</span>
          </Link>
        )}

        <div className="flex-1" />

        {active && active.status !== 'indexed' && (
          <Link
            to="/projects"
            className="flex items-center gap-1.5 px-2.5 py-1 rounded-md text-[10px] text-warning
                       bg-warning/10 hover:bg-warning/20 transition-colors"
            title={`${active.name} — ${active.status}`}
          >
            <span className="w-1.5 h-1.5 rounded-full bg-warning" />
            needs onboarding
          </Link>
        )}

        <button
          onClick={() => setContextPackOpen(true)}
          className="hidden sm:flex items-center gap-1.5 px-2.5 py-1.5 rounded-md bg-accent/10 border border-accent/20
                     hover:bg-accent/20 text-accent text-xs font-medium transition-colors cursor-pointer"
          title="Generate token-budgeted context pack for LLMs"
        >
          <Sparkles className="w-3.5 h-3.5" />
          <span>AI Context Pack</span>
        </button>

        <button
          onClick={() => setCommandPaletteOpen(true)}
          className="flex items-center gap-2 px-3 py-1.5 rounded-md bg-surface-raised border border-border-subtle
                     hover:border-border text-text-muted text-xs transition-colors cursor-pointer"
        >
          <Search className="w-3 h-3" />
          <span>Search commands...</span>
          <kbd className="ml-2 px-1.5 py-0.5 rounded bg-bg border border-border-subtle text-[10px] font-mono">
            <Command className="w-2.5 h-2.5 inline" />K
          </kbd>
        </button>

        <StatusDot level={status.connection} />
      </header>

      <ContextPackModal
        isOpen={contextPackOpen}
        onClose={() => setContextPackOpen(false)}
      />
    </>
  )
}

function StatusDot({ level }: { level: string }) {
  const color = {
    ok: 'bg-success',
    warn: 'bg-warning',
    error: 'bg-error',
    loading: 'bg-zinc-500 animate-pulse',
  }[level] ?? 'bg-zinc-500'
  return <div className={`w-2 h-2 rounded-full ${color}`} title={`Status: ${level}`} />
}