import { useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'
import { useAppStore } from '@/stores/app'

export function useStatusPoll() {
  const setStatus = useAppStore((s) => s.setStatus)

  const query = useQuery({
    queryKey: ['status'],
    queryFn: api.getStatus,
    refetchInterval: 5_000,
  })

  useEffect(() => {
    if (!query.data) return
    const d = query.data
    setStatus({
      daemon: d.daemon.running ? 'ok' : 'warn',
      daemonPid: d.daemon.pid,
      index: d.index.fresh ? 'ok' : 'warn',
      indexAge: d.index.last_sync,
      embedder: d.embedder.ready ? 'ok' : d.embedder.warming ? 'loading' : 'error',
      embedderBackend: d.embedder.backend,
    })
  }, [query.data, setStatus])

  return query
}
