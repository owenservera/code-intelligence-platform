import { useState, useEffect, useRef, useCallback, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAppStore } from '@/stores/app'
import { api, searchApi, type CommandInfo } from '@/lib/api'
import { useQuery } from '@tanstack/react-query'
import { Search, X, Loader2, FileCode, ChevronLeft } from 'lucide-react'
import { cn } from '@/lib/utils'
import { CommandForm } from './CommandForm'

interface PaletteRow {
  kind: 'command' | 'code'
  name: string
  description: string
  meta: string
  cmd?: CommandInfo
  path?: string
}

export function CommandPalette() {
  const open = useAppStore((s) => s.commandPaletteOpen)
  const setOpen = useAppStore((s) => s.setCommandPaletteOpen)
  const navigate = useNavigate()
  const [query, setQuery] = useState('')
  const [selectedIdx, setSelectedIdx] = useState(0)
  const [executing, setExecuting] = useState<string | null>(null)
  const [detail, setDetail] = useState<CommandInfo | null>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  const { data: commands } = useQuery({
    queryKey: ['commands'],
    queryFn: api.getCommands,
    enabled: open,
  })

  // Hybrid: query code backend when user types
  const { data: searchData, isFetching: searching } = useQuery({
    queryKey: ['palette-search', query],
    queryFn: () => searchApi.search(query, { k: 4 }),
    enabled: open && query.trim().length >= 2,
  })

  const rows: PaletteRow[] = useMemo(() => {
    const cmdRows: PaletteRow[] = (commands?.categories ?? [])
      .flatMap((cat) => cat.commands)
      .filter(
        (c) =>
          c.name.toLowerCase().includes(query.toLowerCase()) ||
          c.description.toLowerCase().includes(query.toLowerCase()) ||
          c.category.toLowerCase().includes(query.toLowerCase()),
      )
      .slice(0, 8)
      .map((c) => ({
        kind: 'command' as const,
        name: c.name,
        description: c.description,
        meta: c.category,
        cmd: c,
      }))
    const codeRows: PaletteRow[] = (searchData?.results ?? []).map((r) => ({
      kind: 'code' as const,
      name: r.path,
      description: r.snippet.slice(0, 80) || 'code match',
      meta: `score ${r.score.toFixed(2)}`,
      path: r.path,
    }))
    return [...codeRows, ...cmdRows]
  }, [commands, searchData, query])

  useEffect(() => {
    if (open) {
      setQuery('')
      setSelectedIdx(0)
      setDetail(null)
      setTimeout(() => inputRef.current?.focus(), 50)
    }
  }, [open])

  const executeCommand = useCallback(
    async (cmd: CommandInfo, params: Record<string, unknown>) => {
      try {
        setExecuting(cmd.name)
        await api.runCommand(cmd.name, params)
        setOpen(false)
      } catch (err) {
        console.error('Command failed:', err)
      } finally {
        setExecuting(null)
      }
    },
    [setOpen],
  )

  const openCommand = useCallback(
    (cmd: CommandInfo) => {
      // commands with params open a detail form stage; param-less run immediately
      if (cmd.params.length > 0) setDetail(cmd)
      else executeCommand(cmd, {})
    },
    [executeCommand],
  )

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === 'ArrowDown') {
        e.preventDefault()
        setSelectedIdx((i) => Math.min(i + 1, rows.length - 1))
      } else if (e.key === 'ArrowUp') {
        e.preventDefault()
        setSelectedIdx((i) => Math.max(i - 1, 0))
      } else if (e.key === 'Enter' && rows[selectedIdx]) {
        e.preventDefault()
        const row = rows[selectedIdx]
        if (row.kind === 'code') {
          navigate(`/search?q=${encodeURIComponent(query)}`)
          setOpen(false)
        } else if (row.cmd) {
          openCommand(row.cmd)
        }
      } else if (e.key === 'Escape') {
        if (detail) setDetail(null)
        else setOpen(false)
      }
    },
    [rows, selectedIdx, setOpen, query, navigate, detail, openCommand],
  )

  if (!open) return null

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center pt-[15vh]">
      <div className="fixed inset-0 bg-black/60" onClick={() => setOpen(false)} />
      <div className="relative w-full max-w-lg bg-surface border border-border rounded-xl shadow-2xl overflow-hidden">
        <div className="flex items-center gap-2 px-4 border-b border-border">
          <Search className="w-4 h-4 text-text-muted shrink-0" />
          <input
            ref={inputRef}
            value={query}
            onChange={(e) => { setQuery(e.target.value); setSelectedIdx(0) }}
            onKeyDown={handleKeyDown}
            placeholder="Search commands and code…"
            className="flex-1 py-3 bg-transparent text-sm text-text-primary outline-none placeholder:text-text-muted"
          />
          {searching && <Loader2 className="w-4 h-4 animate-spin text-accent shrink-0" />}
          <button onClick={() => setOpen(false)} className="text-text-muted hover:text-text-primary cursor-pointer">
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="max-h-80 overflow-y-auto p-1">
          {detail ? (
            <>
              <button
                onClick={() => setDetail(null)}
                className="w-full flex items-center gap-2 px-3 py-2 rounded-lg text-left text-sm text-text-secondary hover:bg-surface-raised transition-colors cursor-pointer"
              >
                <ChevronLeft className="w-4 h-4 shrink-0" />
                <span className="font-mono text-text-primary">{detail.name}</span>
                <span className="text-[11px] text-text-muted truncate">{detail.category}</span>
              </button>
              <CommandForm
                command={detail}
                submitting={executing === detail.name}
                onCancel={() => setDetail(null)}
                onSubmit={(params) => executeCommand(detail, params)}
              />
            </>
          ) : (
            <>
              {rows.length === 0 ? (
                <p className="py-6 text-center text-sm text-text-muted">
                  {query ? 'No matches' : 'Type to search commands & code'}
                </p>
              ) : null}
              {rows.map((row, i) => (
            <button
              key={`${row.kind}:${row.name}:${i}`}
              onClick={() => {
                if (row.kind === 'code') { navigate(`/search?q=${encodeURIComponent(query)}`); setOpen(false) }
                else if (row.cmd) openCommand(row.cmd)
              }}
              onMouseEnter={() => setSelectedIdx(i)}
              className={cn(
                'w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-left text-sm transition-colors cursor-pointer',
                i === selectedIdx ? 'bg-accent/15 text-accent' : 'text-text-secondary hover:bg-surface-raised',
              )}
            >
              {row.kind === 'code' ? (
                <FileCode className="w-4 h-4 text-success shrink-0" />
              ) : executing === row.name ? (
                <Loader2 className="w-4 h-4 animate-spin shrink-0" />
              ) : (
                <span className="text-text-muted w-4 shrink-0">›</span>
              )}
              <span className="flex-1 min-w-0">
                <span className={cn('block truncate text-xs', row.kind === 'code' ? 'text-text-primary' : 'font-mono')}>
                  {row.name}
                </span>
                <span className="block truncate text-[11px] text-text-muted">{row.description}</span>
              </span>
              <span className="ml-2 text-[10px] text-text-muted shrink-0">{row.meta}</span>
              </button>
            ))}
            </>
          )}
        </div>

        <div className="flex items-center gap-4 px-4 py-2 border-t border-border text-[10px] text-text-muted font-mono">
          <span><kbd className="px-1 py-0.5 rounded bg-surface-raised border border-border-subtle">↑↓</kbd> navigate</span>
          <span><kbd className="px-1 py-0.5 rounded bg-surface-raised border border-border-subtle">↵</kbd> open</span>
          <span><kbd className="px-1 py-0.5 rounded bg-surface-raised border border-border-subtle">esc</kbd> close</span>
        </div>
      </div>
    </div>
  )
}