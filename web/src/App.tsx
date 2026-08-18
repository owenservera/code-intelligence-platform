import { useEffect, useState } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { Loader2 } from 'lucide-react'
import { AppShell } from './components/layout/AppShell'
import { CommandCenter } from './views/CommandCenter'
import { DaemonView } from './views/DaemonView'
import { IndexView } from './views/IndexView'
import { SearchView } from './views/SearchView'
import { FileView } from './views/FileView'
import { QualityView } from './views/QualityView'
import { MemoryView } from './views/MemoryView'
import { VisualizeView } from './views/VisualizeView'
import { SettingsView } from './views/SettingsView'
import { ExportView } from './views/ExportView'
import { OracleView } from './views/OracleView'
import { ProjectsView } from './views/ProjectsView'
import { OnboardingView } from './views/OnboardingView'
import { onboardingApi, projectsApi } from './lib/api'
import { useAppStore } from './stores/app'

const SKIP_KEY = 'cip:onboarding:skipped'

export default function App() {
  const activeProject = useAppStore((s) => s.activeProject)
  const setActiveProject = useAppStore((s) => s.setActiveProject)
  const setProjects = useAppStore((s) => s.setProjects)
  const projects = useAppStore((s) => s.projects)

  // Registry list — no ?repo= (registry-level). Resolved once; the store seeds
  // activeProject from localStorage and App reconciles it against reality.
  const projectsQ = useQuery({
    queryKey: ['projects'],
    queryFn: projectsApi.list,
  })

  // GAP-06: reconcile the persisted activeProject against the live registry. If
  // the stored id is gone (unregistered) or nothing is stored, fall back to the
  // first registered project; null only when the registry is empty (registry-mode
  // boot with zero projects → the /projects dashboard is the entry point).
  useEffect(() => {
    if (!projectsQ.data) return
    const list = projectsQ.data.projects ?? []
    setProjects(list)
    const known = list.some((p) => p.id === activeProject)
    if (!known) {
      setActiveProject(list.length ? list[0].id : null)
    }
  }, [projectsQ.data, activeProject, setActiveProject, setProjects])

  // SPEC-12 first-run gate — scoped to the ACTIVE project (GAP-06): every read
  // carries ?repo= via request<T>, so this query reflects only the selected repo.
  const onboarding = useQuery({
    queryKey: ['onboarding', activeProject],
    queryFn: () => onboardingApi.status(),
    enabled: Boolean(activeProject),
    // Only keep polling while the wizard is actually shown (detector walks the tree).
    refetchInterval: (query) => (query.state.data?.needs_onboarding ? 8_000 : false),
  })
  const [skipped, setSkipped] = useState(() => localStorage.getItem(SKIP_KEY) === '1')

  const dismiss = () => {
    localStorage.setItem(SKIP_KEY, '1')
    setSkipped(true)
  }
  const onIndexed = () => {
    localStorage.removeItem(SKIP_KEY)
    setSkipped(false)
    onboarding.refetch()
  }

  // Registry-mode entry: no projects yet → land on the /projects dashboard.
  if (projectsQ.isLoading) return <Splash />
  if (!projects.length) {
    return (
      <Routes>
        <Route element={<AppShell />}>
          <Route index element={<ProjectsView />} />
          <Route path="/projects" element={<ProjectsView />} />
          <Route path="*" element={<Navigate to="/projects" replace />} />
        </Route>
      </Routes>
    )
  }
  if (!activeProject) return <Splash />

  // Per-project gate: the wizard only renders for the selected project.
  if (onboarding.data?.needs_onboarding && !skipped) {
    return <OnboardingView status={onboarding.data} onSkip={dismiss} onIndexed={onIndexed} />
  }

  return (
    <Routes>
      <Route element={<AppShell />}>
        <Route index element={<CommandCenter />} />
        <Route path="/daemon" element={<DaemonView />} />
        <Route path="/index" element={<IndexView />} />
        <Route path="/search" element={<SearchView />} />
        <Route path="/files" element={<FileView />} />
        <Route path="/quality" element={<QualityView />} />
        <Route path="/memory" element={<MemoryView />} />
        <Route path="/visualize" element={<VisualizeView />} />
        <Route path="/settings" element={<SettingsView />} />
        <Route path="/export" element={<ExportView />} />
        <Route path="/oracle" element={<OracleView />} />
        <Route path="/projects" element={<ProjectsView />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  )
}

function Splash() {
  return (
    <div className="min-h-screen bg-bg flex items-center justify-center">
      <div className="flex items-center gap-2 text-text-muted text-sm">
        <Loader2 className="w-4 h-4 animate-spin text-accent" /> Checking repo state…
      </div>
    </div>
  )
}