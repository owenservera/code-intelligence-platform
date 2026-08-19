import { create } from 'zustand'

export type StatusLevel = 'ok' | 'warn' | 'error' | 'loading'

export interface StatusCluster {
  connection: StatusLevel
  daemon: StatusLevel
  index: StatusLevel
  embedder: StatusLevel
  daemonPid: number | null
  indexAge: string | null
  embedderBackend: string | null
}

export interface ProjectSummary {
  id: string
  root: string
  name: string
  status: string
  last_onboard_ts: number | null
  repo_type: string | null
}

const ACTIVE_KEY = 'cip:activeProject'
const EXPLORER_COLLAPSED_KEY = 'cip:explorerCollapsed'
const LEFTNAV_COLLAPSED_KEY = 'cip:leftnavCollapsed'
const INTELLIGENCE_COLLAPSED_KEY = 'cip:intelligenceCollapsed'

export function getActiveProject(): string | null {
  return useAppStore.getState().activeProject
}

export interface AppState {
  status: StatusCluster
  setStatus: (s: Partial<StatusCluster>) => void
  commandPaletteOpen: boolean
  toggleCommandPalette: () => void
  setCommandPaletteOpen: (open: boolean) => void
  // ── SPEC-19 §3/§6: active project + registry (P6) ────────────────────────
  activeProject: string | null
  projects: ProjectSummary[]
  setActiveProject: (id: string | null) => void
  setProjects: (list: ProjectSummary[]) => void
  // ── SPEC-16 §3: explorer tree state (P8) ──────────────────────────────────
  activePath: string | null
  setActivePath: (path: string | null) => void
  expanded: Record<string, boolean>
  setExpanded: (dir: string, expanded: boolean) => void
  loadingDir: string | null
  setLoadingDir: (dir: string | null) => void
  // PLAN-08 T8.4: bumped on every file.changed WS event so RepoExplorer can
  // invalidate its local /api/tree cache for the changed file's dir.
  fileChangeEpoch: number
  lastChangedPath: string | null
  bumpFileChange: (path?: string | null) => void
  // ── Real estate: collapsible panels (P8) ────────────────────────────────
  explorerCollapsed: boolean
  toggleExplorerCollapsed: () => void
  leftnavCollapsed: boolean
  toggleLeftnavCollapsed: () => void
  intelligenceCollapsed: boolean
  toggleIntelligenceCollapsed: () => void
}

export const useAppStore = create<AppState>((set) => ({
  status: {
    connection: 'loading',
    daemon: 'loading',
    index: 'loading',
    embedder: 'loading',
    daemonPid: null,
    indexAge: null,
    embedderBackend: null,
  },
  setStatus: (s) => set((prev) => ({ status: { ...prev.status, ...s } })),
  commandPaletteOpen: false,
  toggleCommandPalette: () => set((prev) => ({ commandPaletteOpen: !prev.commandPaletteOpen })),
  setCommandPaletteOpen: (open) => set({ commandPaletteOpen: open }),
  activeProject: localStorage.getItem(ACTIVE_KEY),
  projects: [],
  setActiveProject: (id) => {
    if (id) localStorage.setItem(ACTIVE_KEY, id)
    else localStorage.removeItem(ACTIVE_KEY)
    set({ activeProject: id })
    // P8: reset the explorer view on project switch — a different repo has a
    // different tree; keep activePath/expanded stale-free (PLAN-08 T8.2).
    set({ activePath: null, expanded: {}, loadingDir: null })
  },
  setProjects: (list) => set({ projects: list }),
  activePath: null,
  setActivePath: (path) => set({ activePath: path }),
  expanded: {},
  setExpanded: (dir, expanded) =>
    set((prev) => ({ expanded: { ...prev.expanded, [dir]: expanded } })),
  loadingDir: null,
  setLoadingDir: (dir) => set({ loadingDir: dir }),
  fileChangeEpoch: 0,
  lastChangedPath: null,
  bumpFileChange: (path) =>
    set((prev) => ({ fileChangeEpoch: prev.fileChangeEpoch + 1, lastChangedPath: path ?? null })),
  explorerCollapsed: localStorage.getItem(EXPLORER_COLLAPSED_KEY) === '1',
  toggleExplorerCollapsed: () =>
    set((prev) => {
      const next = !prev.explorerCollapsed
      localStorage.setItem(EXPLORER_COLLAPSED_KEY, next ? '1' : '0')
      return { explorerCollapsed: next }
    }),
  leftnavCollapsed: localStorage.getItem(LEFTNAV_COLLAPSED_KEY) === '1',
  toggleLeftnavCollapsed: () =>
    set((prev) => {
      const next = !prev.leftnavCollapsed
      localStorage.setItem(LEFTNAV_COLLAPSED_KEY, next ? '1' : '0')
      return { leftnavCollapsed: next }
    }),
  intelligenceCollapsed: localStorage.getItem(INTELLIGENCE_COLLAPSED_KEY) === '1',
  toggleIntelligenceCollapsed: () =>
    set((prev) => {
      const next = !prev.intelligenceCollapsed
      localStorage.setItem(INTELLIGENCE_COLLAPSED_KEY, next ? '1' : '0')
      return { intelligenceCollapsed: next }
    }),
}))