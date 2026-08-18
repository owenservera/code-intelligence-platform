import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import {
  FolderPlus,
  FolderOpen,
  Rocket,
  Trash2,
  Loader2,
  CheckCircle2,
  AlertTriangle,
  RefreshCw,
  ExternalLink,
} from 'lucide-react'
import { projectsApi, type ProjectSummary } from '@/lib/api'
import { useAppStore } from '@/stores/app'

// SPEC-19 §3: the /projects dashboard — list, register, remove, open, onboard.
export function ProjectsView() {
  const navigate = useNavigate()
  const qc = useQueryClient()
  const activeProject = useAppStore((s) => s.activeProject)
  const setActiveProject = useAppStore((s) => s.setActiveProject)
  const setProjects = useAppStore((s) => s.setProjects)
  const [path, setPath] = useState('')
  const [adding, setAdding] = useState(false)
  const [addError, setAddError] = useState<string | null>(null)
  const [busy, setBusy] = useState<string | null>(null)
  const [removing, setRemoving] = useState<string | null>(null)

  const list = useQuery({
    queryKey: ['projects'],
    queryFn: projectsApi.list,
    refetchInterval: 15_000,
  })

  const projects = list.data?.projects ?? []

  const open = (p: ProjectSummary) => {
    setActiveProject(p.id)
    // project.onboarded / index.update events invalidate these when they land
    void qc.invalidateQueries({ queryKey: ['status'] })
    void qc.invalidateQueries({ queryKey: ['onboarding'] })
    navigate('/')
  }

  const addProject = async () => {
    const root = path.trim()
    if (!root) return
    setAdding(true)
    setAddError(null)
    try {
      const created = await projectsApi.register(root)
      setProjects([...projects, created])
      setPath('')
      // refresh the authoritative list (status/repo_type enrichment)
      await list.refetch()
      void qc.invalidateQueries({ queryKey: ['projects'] })
    } catch (e) {
      setAddError(String(e))
    } finally {
      setAdding(false)
    }
  }

  const onboard = async (p: ProjectSummary) => {
    setBusy(p.id)
    try {
      await projectsApi.onboard(p.id)
      setActiveProject(p.id)
      await list.refetch()
      navigate('/')
    } catch (e) {
      alert(`Onboard failed: ${String(e)}`)
    } finally {
      setBusy(null)
    }
  }

  const remove = async (p: ProjectSummary) => {
    if (!window.confirm(`Remove "${p.name}" from CIP? Files are never deleted.`)) return
    setRemoving(p.id)
    try {
      await projectsApi.remove(p.id)
      await list.refetch()
      if (activeProject === p.id) setActiveProject(null)
    } catch (e) {
      alert(`Remove failed: ${String(e)}`)
    } finally {
      setRemoving(null)
    }
  }

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-text-primary mb-1">Projects</h1>
        <p className="text-text-muted text-sm">
          Every repo CIP indexes lives here. Switch, add, or initialize — each project keeps its own index, watch, and daemon.
        </p>
      </div>

      {/* Register a folder */}
      <section className="rounded-lg border border-border bg-surface p-5 space-y-3">
        <h2 className="text-sm font-medium text-text-secondary flex items-center gap-2">
          <FolderPlus className="w-4 h-4 text-accent" /> Add a project
        </h2>
        <div className="flex gap-2">
          <input
            value={path}
            onChange={(e) => setPath(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && void addProject()}
            placeholder="C:\path\to\repo  (any folder, no CIP files required)"
            className="flex-1 px-3 py-2 rounded-md bg-bg border border-border-subtle text-xs font-mono
                       text-text-primary placeholder:text-text-muted focus:border-accent outline-none"
          />
          <Button onClick={() => void addProject()} disabled={!path.trim() || adding}>
            {adding ? <Loader2 className="w-4 h-4 animate-spin" /> : <FolderPlus className="w-4 h-4" />}
            Add
          </Button>
        </div>
        {addError && (
          <p className="text-xs text-error flex items-center gap-1.5">
            <AlertTriangle className="w-3 h-3" /> {addError}
          </p>
        )}
      </section>

      {/* Grid of cards */}
      {projects.length === 0 ? (
        <div className="rounded-lg border border-dashed border-border-subtle p-12 text-center text-sm text-text-muted">
          No projects yet — register a folder above to get started.
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {projects.map((p) => (
            <div
              key={p.id}
              className={`rounded-lg border bg-surface p-5 space-y-3 ${
                p.id === activeProject ? 'border-accent' : 'border-border'
              }`}
            >
              <div className="flex items-start gap-3">
                <FolderOpen className="w-5 h-5 text-accent shrink-0 mt-0.5" />
                <div className="min-w-0">
                  <p className="text-sm font-medium text-text-primary truncate">{p.name}</p>
                  <p className="text-[11px] font-mono text-text-muted truncate" title={p.root}>
                    {p.root}
                  </p>
                </div>
                <div className="flex-1" />
                <StatusChip status={p.status} />
              </div>

              <div className="flex items-center gap-3 text-[11px] text-text-muted">
                {p.repo_type && (
                  <span className="px-2 py-0.5 rounded bg-surface-raised border border-border-subtle">
                    {p.repo_type}
                  </span>
                )}
                {p.last_onboard_ts ? (
                  <span className="flex items-center gap-1">
                    <CheckCircle2 className="w-3 h-3 text-success" /> onboarded
                  </span>
                ) : (
                  <span className="flex items-center gap-1 text-warning">
                    <AlertTriangle className="w-3 h-3" /> not initialized
                  </span>
                )}
              </div>

              <div className="flex gap-2 pt-1">
                <Button variant="primary" onClick={() => open(p)} disabled={busy === p.id}>
                  {busy === p.id ? <Loader2 className="w-4 h-4 animate-spin" /> : <ExternalLink className="w-3.5 h-3.5" />}
                  Open
                </Button>
                {p.status !== 'indexed' && (
                  <Button onClick={() => void onboard(p)} disabled={busy === p.id}>
                    <Rocket className="w-3.5 h-3.5" /> Onboard
                  </Button>
                )}
                <Button onClick={() => void list.refetch()} title="Refresh status">
                  <RefreshCw className="w-3.5 h-3.5" />
                </Button>                <div className="flex-1" />
                <Button variant="danger" onClick={() => void remove(p)} disabled={removing === p.id}>
                  <Trash2 className="w-3.5 h-3.5" />
                </Button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

function StatusChip({ status }: { status: string }) {
  const map: Record<string, { color: string; label: string }> = {
    indexed: { color: 'text-success bg-success/10 border-success/30', label: 'indexed' },
    initialized: { color: 'text-warning bg-warning/10 border-warning/30', label: 'initialized' },
    stale: { color: 'text-warning bg-warning/10 border-warning/30', label: 'stale index' },
    no_cip: { color: 'text-text-muted bg-surface-raised border-border-subtle', label: 'no .cip' },
    error: { color: 'text-error bg-error/10 border-error/30', label: 'error' },
  }
  const c = map[status] ?? map.no_cip
  return (
    <span className={`px-2 py-0.5 rounded-full text-[10px] font-medium border ${c.color}`}>{c.label}</span>
  )
}

function Button({
  children,
  onClick,
  variant = 'default',
  disabled,
  title,
}: {
  children: React.ReactNode
  onClick?: () => void
  variant?: 'default' | 'primary' | 'danger'
  disabled?: boolean
  title?: string
}) {
  const styles =
    variant === 'primary'
      ? 'bg-accent text-bg hover:opacity-90'
      : variant === 'danger'
        ? 'text-error border border-error/40 hover:bg-error/10'
        : 'text-text-secondary hover:text-text-primary border border-border-subtle hover:border-border'
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      title={title}
      className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium cursor-pointer transition-colors disabled:opacity-50 ${styles}`}
    >
      {children}
    </button>
  )
}