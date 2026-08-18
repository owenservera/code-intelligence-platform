import { create } from 'zustand'
import type { JobEvent } from '@/lib/api'

export interface FeedLine {
  id: string
  ts: number
  type: JobEvent['type']
  command?: string
  message: string
}

const MAX_ROWS = 200

// GAP-07: append-buffer for non-job live events (watch.event / index.update /
// quality.update / memory.updated / config.update / signals.ingested). Views
// that show activity render the tail of this buffer; polling is the fallback.
export interface EventsState {
  lines: FeedLine[]
  push: (ev: JobEvent) => void
  clear: () => void
}

function lineFor(ev: JobEvent): FeedLine | null {
  const d = ev.data as Record<string, unknown> | null | undefined
  switch (ev.type) {
    case 'watch.event':
      return {
        id: ev.job_id ?? `${ev.type}-${ev.timestamp}`,
        ts: ev.timestamp ?? Date.now() / 1000,
        type: ev.type,
        command: ev.command,
        message: String((d as { event?: string })?.event ?? 'watch event'),
      }
    case 'index.update':
      return {
        id: ev.job_id ?? `${ev.type}-${ev.timestamp}`,
        ts: ev.timestamp ?? Date.now() / 1000,
        type: ev.type,
        command: ev.command,
        message: 'index updated',
      }
    case 'quality.update':
      return {
        id: ev.job_id ?? `${ev.type}-${ev.timestamp}`,
        ts: ev.timestamp ?? Date.now() / 1000,
        type: ev.type,
        command: ev.command,
        message: 'quality refreshed',
      }
    case 'memory.updated':
      return {
        id: ev.job_id ?? `${ev.type}-${ev.timestamp}`,
        ts: ev.timestamp ?? Date.now() / 1000,
        type: ev.type,
        command: ev.command,
        message: 'memory updated',
      }
    case 'config.update':
      return {
        id: ev.job_id ?? `${ev.type}-${ev.timestamp}`,
        ts: ev.timestamp ?? Date.now() / 1000,
        type: ev.type,
        command: ev.command,
        message: 'config updated',
      }
    case 'signals.ingested':
      return {
        id: ev.job_id ?? `${ev.type}-${ev.timestamp}`,
        ts: ev.timestamp ?? Date.now() / 1000,
        type: ev.type,
        command: ev.command,
        message: 'signals ingested',
      }
    case 'workflow.step':
      return {
        id: ev.job_id ?? `${ev.type}-${ev.timestamp}`,
        ts: ev.timestamp ?? Date.now() / 1000,
        type: ev.type,
        command: ev.command,
        message: `workflow step ${(d as { step?: string })?.step ?? ''}`,
      }
    default:
      return null
  }
}

export const useEventsStore = create<EventsState>((set) => ({
  lines: [],
  push: (ev) => {
    const line = lineFor(ev)
    if (!line) return
    set((s) => ({ lines: [...s.lines.slice(-(MAX_ROWS - 1)), line] }))
  },
  clear: () => set({ lines: [] }),
}))
