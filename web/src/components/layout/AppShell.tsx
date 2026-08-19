import { useEffect, useRef } from 'react'
import { Outlet } from 'react-router-dom'
import { useQueryClient } from '@tanstack/react-query'
import { ChevronLeft, ChevronRight } from 'lucide-react'
import { TopBar } from './TopBar'
import { LeftNav } from './LeftNav'
import { RepoExplorer } from '../file/RepoExplorer'
import { StatusBar } from './StatusBar'
import { CommandPalette } from '../command-center/CommandPalette'
import { JobToasts } from '../jobs/JobToasts'
import { useStatusPoll } from '@/hooks/useStatusPoll'
import { useWebSocket } from '@/hooks/useWebSocket'
import { useAppStore } from '@/stores/app'
import { useJobsStore } from '@/stores/jobs'
import { useEventsStore } from '@/stores/events'
import { jobApi, watchApi } from '@/lib/api'
import type { JobEvent } from '@/lib/api'

// GAP-07: every non-job event type routes to its react-query consumer; polling
// becomes the fallback, not the default (SPEC-14 §3 "Event bus → UI"). Keys are
// prefix-matched against the real query keys used by the views.
const EVENT_INVALIDATE: Partial<Record<JobEvent['type'], string[]>> = {
  'index.update': ['index-status', 'watch-status', 'snapshots', 'vis-overview', 'vis-trend'],
  'quality.update': ['quality-bundle', 'quality-findings', 'vis-overview', 'vis-trend'],
  'memory.updated': [
    'memory-overview',
    'memory-facts',
    'memory-episodes',
    'memory-patterns',
    'memory-suggestions',
  ],
  'config.update': ['config-bundle', 'config-schema', 'config-env'],
  'verify.done': ['export-status', 'export-tools', 'quality-bundle'],
  'signals.ingested': ['vis-signals'],
  'daemon.status': ['daemon-status', 'embed-status', 'daemon-log'],
  'watch.event': ['watch-status', 'index-status'],
  // PLAN-08 T8.4: a file changed on disk (watcher, PLAN-05) → refresh the open
  // file panel + its summary/impact/history caches. The tree's own cache is
  // busted separately via the fileChangeEpoch counter (see below).
  'file.changed': ['file', 'file-summary', 'file-impact', 'file-history'],
}

export function AppShell() {
  useStatusPoll()
  const setCommandPaletteOpen = useAppStore((s) => s.setCommandPaletteOpen)
  const explorerCollapsed = useAppStore((s) => s.explorerCollapsed)
  const toggleExplorerCollapsed = useAppStore((s) => s.toggleExplorerCollapsed)
  const upsert = useJobsStore((s) => s.upsert)
  const seed = useJobsStore((s) => s.seed)
  const pushFeed = useEventsStore((s) => s.push)
  const qc = useQueryClient()
  // SPEC-19 §6: re-scope polling + job history when the active project changes.
  const activeProject = useAppStore((s) => s.activeProject)
  const bumpFileChange = useAppStore((s) => s.bumpFileChange)
  const lastProject = useRef<string | null>(null)

  // PLAN-05 T5.3: lazily (de)activate this project's watcher. Runs on switch and
  // on mount so the shell always mirrors the active project's watch state.
  useEffect(() => {
    const prev = lastProject.current
    lastProject.current = activeProject
    if (activeProject) void watchApi.activate(activeProject, true)
    if (prev && prev !== activeProject) void watchApi.activate(prev, false)
  }, [activeProject])

  // Seed job history once per project so the toast stack / history view have
  // data even before any live events arrive (SPEC-02 §4) — and refetch on switch.
  useEffect(() => {
    jobApi
      .list()
      .then((r) => seed(r.jobs))
      .catch(() => {})
    void qc.invalidateQueries({ queryKey: ['status'] })
    void qc.invalidateQueries({ queryKey: ['onboarding'] })
  }, [activeProject, seed, qc])

  // Route live WS events: job events → job store; non-job events → activity
  // buffer + react-query invalidation.
  useWebSocket([
    (ev) => {
      upsert(ev)
      pushFeed(ev)
      if (ev.type === 'file.changed') {
        const d = ev.data as { payload?: { path?: string } } | null
        bumpFileChange(d?.payload?.path ?? null)
      }
      const keys = EVENT_INVALIDATE[ev.type]
      if (keys) {
        for (const key of keys) {
          void qc.invalidateQueries({ queryKey: [key] })
        }
      }
    },
  ])

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault()
        setCommandPaletteOpen(true)
      }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [setCommandPaletteOpen])

  return (
    <div className="h-screen flex flex-col bg-bg">
      <TopBar />
      <div className="flex flex-1 overflow-hidden">
        <LeftNav />
        {/* PLAN-08: collapsible repo explorer rail; keyed by project so the
            cache resets on project switch (PLAN-06). file.changed busts only
            the affected dir via RepoExplorer's epoch subscription (T8.4). */}
        {explorerCollapsed ? (
          <button
            onClick={toggleExplorerCollapsed}
            className="w-8 border-r border-border bg-surface hover:bg-surface-raised flex items-center justify-center shrink-0 transition-colors"
            aria-label="Show file explorer"
            title="Show file explorer"
          >
            <ChevronRight className="w-4 h-4 text-text-muted" />
          </button>
        ) : (
          <>
            <RepoExplorer key={activeProject} />
            <button
              onClick={toggleExplorerCollapsed}
              className="w-8 border-r border-border bg-surface hover:bg-surface-raised flex items-center justify-center shrink-0 transition-colors"
              aria-label="Hide file explorer"
              title="Hide file explorer"
            >
              <ChevronLeft className="w-4 h-4 text-text-muted" />
            </button>
          </>
        )}
        <main className="flex-1 overflow-auto p-6">
          <Outlet />
        </main>
      </div>
      <StatusBar />
      <CommandPalette />
      <JobToasts />
    </div>
  )
}
