import { useEffect, useRef, useCallback } from 'react'
import { useAppStore } from '@/stores/app'
import type { JobEvent, JobEventType } from '@/lib/api'

type WsHandler = (event: JobEvent) => void

const RECONNECT_DELAY = 1000
const MAX_RECONNECT_DELAY = 30000

interface ReplayedEvent {
  ts: number
  kind: string
  payload: unknown
}

export function useWebSocket(handlers?: WsHandler[]) {
  const wsRef = useRef<WebSocket | null>(null)
  const reconnectDelay = useRef(RECONNECT_DELAY)
  const alive = useRef(false)
  const lastTs = useRef<number>(0)
  const setStatus = useAppStore((s) => s.setStatus)
  // SPEC-19 §6.2: subscribe to the active project's WS bucket; switching projects
  // tears down the socket and reconnects with the new ?repo= (PLAN-06 T6.2).
  const activeProject = useAppStore((s) => s.activeProject)

  const connect = useCallback(() => {
    const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:'
    const query = activeProject ? `?repo=${encodeURIComponent(activeProject)}` : ''
    const ws = new WebSocket(`${protocol}//${location.host}/ws${query}`)
    wsRef.current = ws

    ws.onopen = () => {
      alive.current = true
      reconnectDelay.current = RECONNECT_DELAY
      setStatus({ connection: 'ok' })
      // GAP-02: replay durable events missed while disconnected (SPEC-14 §6.2).
      ws.send(JSON.stringify({ type: 'subscribe', since: lastTs.current || undefined }))
    }

    ws.onmessage = (ev) => {
      try {
        const raw = JSON.parse(ev.data)
        if (raw.type === 'events.replay') {
          // Replay reply carries durable rows {ts, kind, payload}; map them back
          // into the JobEvent shape handlers expect.
          for (const r of (raw.events ?? []) as ReplayedEvent[]) {
            const replayed: JobEvent = {
              type: r.kind as JobEventType,
              data: r.payload,
              timestamp: r.ts,
            }
            handlers?.forEach((h) => h(replayed))
          }
        } else {
          const event = raw as JobEvent
          if (typeof event.timestamp === 'number') {
            lastTs.current = Math.max(lastTs.current, event.timestamp)
          }
          handlers?.forEach((h) => h(event))
        }
      } catch {
        /* ignore malformed */
      }
    }

    ws.onclose = () => {
      alive.current = false
      setStatus({ connection: 'error' })
      const delay = reconnectDelay.current
      reconnectDelay.current = Math.min(delay * 2, MAX_RECONNECT_DELAY)
      setTimeout(connect, delay)
    }

    ws.onerror = () => ws.close()
  }, [handlers, setStatus, activeProject])

  useEffect(() => {
    connect()
    return () => {
      // Tear down on unmount OR on project switch; the re-run of `connect` with
      // the new activeProject rebinds the socket to the new bucket.
      alive.current = false
      wsRef.current?.close()
    }
  }, [connect])

  return { send: (data: unknown) => wsRef.current?.send(JSON.stringify(data)) }
}
