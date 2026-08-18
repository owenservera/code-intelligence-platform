import { create } from 'zustand'
import type { JobEvent, JobInfo, JobProgressData } from '@/lib/api'

export interface JobsState {
  jobs: Record<string, JobInfo>
  order: string[]
  upsert: (ev: JobEvent) => void
  seed: (jobs: JobInfo[]) => void
  reset: () => void
}

function progress(ev: JobEvent): Partial<JobInfo> {
  const d = (ev.data ?? {}) as JobProgressData
  return { phase: d.phase, pct: d.pct ?? 0 }
}

function emptyJob(ev: JobEvent): JobInfo {
  return {
    id: ev.job_id!,
    command: ev.command ?? '',
    status: 'running',
    started: Date.now() / 1000,
    logs: [],
    pct: 0,
  }
}

export const useJobsStore = create<JobsState>((set) => ({
  jobs: {},
  order: [],
  seed: (jobs) =>
    set(() => {
      const map: Record<string, JobInfo> = {}
      const order: string[] = []
      for (const j of jobs) {
        map[j.id] = j
        order.push(j.id)
      }
      return { jobs: map, order }
    }),
  upsert: (ev) =>
    set((s) => {
      if (!ev.job_id) return {}
      const prev = s.jobs[ev.job_id]
      let next: JobInfo
      switch (ev.type) {
        case 'job.start':
          next = {
            id: ev.job_id,
            command: ev.command ?? '',
            status: 'running',
            started: Date.now() / 1000,
            logs: [],
            pct: 0,
          }
          break
        case 'job.progress':
          next = { ...(prev ?? emptyJob(ev)), ...progress(ev) }
          break
        case 'job.log':
          next = {
            ...(prev ?? emptyJob(ev)),
            logs: [...(prev?.logs ?? []), (ev.data as { line: string }).line],
          }
          break
        case 'job.done':
          next = {
            ...(prev ?? emptyJob(ev)),
            status: 'done',
            pct: 100,
            finished: Date.now() / 1000,
            result: (ev.data as { result?: unknown; message?: string }).result ?? null,
          }
          break
        case 'job.error':
          next = {
            ...(prev ?? emptyJob(ev)),
            status: 'error',
            error: (ev.data as { message?: string }).message ?? 'failed',
            finished: Date.now() / 1000,
          }
          break
        case 'job.cancelled':
          next = { ...(prev ?? emptyJob(ev)), status: 'cancelled', finished: Date.now() / 1000 }
          break
        default:
          return {}
      }
      const order = s.order.includes(next.id) ? s.order : [...s.order, next.id]
      return { jobs: { ...s.jobs, [next.id]: next }, order }
    }),
  reset: () => set({ jobs: {}, order: [] }),
}))
