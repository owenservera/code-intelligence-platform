import { useState, useEffect } from 'react'
import { useSearchParams, Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { searchApi, type SearchEnvelope, type SymbolInfo } from '@/lib/api'
import { Search, Loader2, FileCode, Crosshair } from 'lucide-react'

type Mode = 'search' | 'symbols'

export function SearchView() {
  const [searchParams] = useSearchParams()
  const initialQ = searchParams.get('q') ?? ''
  const [mode, setMode] = useState<Mode>('search')
  const [query, setQuery] = useState(initialQ)
  const [debounced, setDebounced] = useState(initialQ)
  const [k, setK] = useState(10)
  const [tier, setTier] = useState('')
  const [kind, setKind] = useState('')
  const [selectedSymbol, setSelectedSymbol] = useState<SymbolInfo | null>(null)

  useEffect(() => {
    const t = setTimeout(() => setDebounced(query), 300)
    return () => clearTimeout(t)
  }, [query])

  const search = useQuery({
    queryKey: ['search', debounced, k, tier, kind, mode],
    queryFn: () => searchApi.search(debounced, { k, tier: tier || undefined, kind: kind || undefined }),
    enabled: mode === 'search' && debounced.trim().length > 0,
  })

  const symbols = useQuery({
    queryKey: ['symbols', debounced],
    queryFn: () => searchApi.symbols(debounced),
    enabled: mode === 'symbols' && debounced.trim().length > 0,
  })

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-text-primary mb-1">Search & Navigation</h1>
        <p className="text-text-muted text-sm">
          Hybrid semantic + lexical search across the whole codebase.
        </p>
      </div>

      {/* Search box */}
      <div className="rounded-lg border border-border bg-surface p-3 flex items-center gap-2">
        <Search className="w-4 h-4 text-text-muted shrink-0" />
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter') setDebounced(query)
          }}
          placeholder="Search code, symbols, terms... (hybrid FTS + vectors)"
          className="flex-1 bg-transparent text-sm text-text-primary outline-none placeholder:text-text-muted"
        />
        <div className="flex rounded-md border border-border-subtle overflow-hidden shrink-0">
          <TabBtn active={mode === 'search'} onClick={() => setMode('search')}>Code</TabBtn>
          <TabBtn active={mode === 'symbols'} onClick={() => setMode('symbols')}>Symbols</TabBtn>
        </div>
        <span className="text-[10px] font-mono text-text-muted shrink-0">k={k}</span>
        <input
          type="range"
          min={3}
          max={30}
          value={k}
          onChange={(e) => setK(Number(e.target.value))}
          className="w-20 accent-indigo-500 shrink-0 cursor-pointer"
          title="Result count (k)"
        />
      </div>

      {/* Filters */}
      {mode === 'search' && (
        <div className="flex flex-wrap items-center gap-2 text-xs">
          <select
            value={tier}
            onChange={(e) => setTier(e.target.value)}
            className="rounded-lg border border-border bg-surface-raised/60 px-2 py-1 text-text-secondary outline-none focus:border-accent"
          >
            <option value="">tier: all</option>
            <option value="code">code</option>
            <option value="test">test</option>
            <option value="config">config</option>
          </select>
          <select
            value={kind}
            onChange={(e) => setKind(e.target.value)}
            className="rounded-lg border border-border bg-surface-raised/60 px-2 py-1 text-text-secondary outline-none focus:border-accent"
          >
            <option value="">kind: all</option>
            <option value="class">class</option>
            <option value="function">function</option>
            <option value="method">method</option>
            <option value="variable">variable</option>
          </select>
        </div>
      )}

      {/* Results */}
      <div className="space-y-4">
        {mode === 'search' && !debounced.trim() && (
          <EmptyState msg="Type a query to search. Results include relevance score, matched backend (fts/vec), and tier." />
        )}
        {mode === 'search' && debounced.trim() && search.isFetching && (
          <div className="flex items-center gap-2 text-sm text-text-muted">
            <Loader2 className="w-4 h-4 animate-spin text-accent" /> Searching…
          </div>
        )}
        {mode === 'search' && search.data && <SearchResults env={search.data} />}

        {mode === 'symbols' && !debounced.trim() && (
          <EmptyState msg="Type a symbol name (partial match supported) to find definitions with relation counts." />
        )}
        {mode === 'symbols' && symbols.data && (
          <SymbolList
            symbols={symbols.data.symbols}
            onSelect={(s) => setSelectedSymbol(s)}
          />
        )}
      </div>

      {selectedSymbol && <SymbolDetail symbol={selectedSymbol} onClose={() => setSelectedSymbol(null)} />}

      {query !== debounced && (
        <p className="text-[10px] text-accent font-mono">debounced… (press Enter to search now)</p>
      )}
    </div>
  )
}

function TabBtn({ active, onClick, children }: { active: boolean; onClick: () => void; children: React.ReactNode }) {
  return (
    <button
      onClick={onClick}
      className={`px-3 py-1.5 text-xs transition-colors cursor-pointer ${active ? 'bg-accent/20 text-accent' : 'text-text-muted hover:text-text-primary'}`}
    >
      {children}
    </button>
  )
}

function EmptyState({ msg }: { msg: string }) {
  return (
    <div className="rounded-lg border border-dashed border-border-subtle p-8 text-center text-sm text-text-muted">
      {msg}
    </div>
  )
}

function SearchResults({ env }: { env: SearchEnvelope }) {
  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <p className="text-xs text-text-muted font-mono">
          {env.count} results in {env.took_ms}ms
        </p>
        {env.warming && (
          <span className="text-[10px] px-2 py-0.5 rounded-full bg-warning/10 text-warning font-mono">
            lexical only — start the embed daemon for semantic
          </span>
        )}
      </div>
      {env.results.map((r) => (
        <Link
          key={`${r.path}:${r.chunk}`}
          to={`/files?path=${encodeURIComponent(r.path)}`}
          className="block rounded-lg border border-border-subtle bg-surface hover:border-accent transition-colors p-3"
        >
          <div className="flex items-center gap-2 mb-1.5">
            <FileCode className="w-3.5 h-3.5 text-accent shrink-0" />
            <span className="font-mono text-xs text-text-primary truncate">{r.path}</span>
            <span className="text-xs text-text-muted shrink-0">
              :{r.lines[0]}–{r.lines[1]}
            </span>
            <span className="ml-auto flex gap-1 shrink-0">
              {r.matched.map((m) => (
                <span key={m} className="text-[9px] px-1 py-0.5 rounded bg-accent/10 text-accent font-mono">{m}</span>
              ))}
              <span className="text-[9px] px-1 py-0.5 rounded bg-surface-raised text-text-muted font-mono">{r.tier}</span>
            </span>
          </div>
          <p className="font-mono text-[11px] leading-5 text-zinc-300 line-clamp-2">{r.snippet}</p>
          <div className="mt-1.5 flex items-center gap-2 text-[11px] text-text-muted">
            <span className="font-mono">score {r.score.toFixed(4)}</span>
            {r.symbol && (
              <Link to={`/files?path=${encodeURIComponent(r.path)}&symbol=${encodeURIComponent(r.symbol)}`} className="text-accent hover:underline font-mono">
                #{r.symbol}
              </Link>
            )}
          </div>
        </Link>
      ))}
    </div>
  )
}

function SymbolList({ symbols, onSelect }: { symbols: SymbolInfo[]; onSelect: (s: SymbolInfo) => void }) {
  if (!symbols.length) return <EmptyState msg="No symbols found." />
  return (
    <div className="space-y-2">
      {symbols.map((s) => (
        <button
          key={s.id}
          onClick={() => onSelect(s)}
          className="w-full rounded-lg border border-border-subtle bg-surface hover:border-accent/50 transition-colors p-3 text-left cursor-pointer"
        >
          <div className="flex items-center gap-2 mb-1">
            <Crosshair className="w-3.5 h-3.5 text-accent shrink-0" />
            <span className="text-sm text-text-primary font-mono">{s.name}</span>
            <span className="text-[10px] px-1.5 py-0.5 rounded bg-surface-raised text-text-muted font-mono">{s.kind}</span>
            <span className="ml-auto text-[10px] text-text-muted font-mono">{s.path}:{s.start_line}</span>
          </div>
          {s.signature && <p className="font-mono text-[11px] text-zinc-400 line-clamp-1">{s.signature}</p>}
          <p className="mt-1 text-[10px] text-text-muted font-mono">
            ↑{Object.entries(s.counts.out).map(([k, v]) => `${k}:${v}`).join(' ') || '—'}
            {' · '}
            ↓{Object.entries(s.counts.in).map(([k, v]) => `${k}:${v}`).join(' ') || '—'}
          </p>
        </button>
      ))}
    </div>
  )
}

function SymbolDetail({ symbol, onClose }: { symbol: SymbolInfo; onClose: () => void }) {
  const graph = useQuery({
    queryKey: ['graph', symbol.id],
    queryFn: () => searchApi.graph(symbol.id, 'both', 1),
    enabled: !!symbol.id,
  })

  const context = useQuery({
    queryKey: ['context', symbol.id],
    queryFn: () => searchApi.context({ symbol: symbol.id }),
    enabled: !!symbol.id,
  })

  return (
    <div className="rounded-lg border border-border bg-surface p-5 space-y-4">
      <div className="flex items-center gap-2">
        <h2 className="text-sm font-medium text-text-primary font-mono">{symbol.name}</h2>
        <span className="text-[10px] px-1.5 py-0.5 rounded bg-surface-raised text-text-muted font-mono">{symbol.kind}</span>
        <button onClick={onClose} className="ml-auto text-xs text-text-muted hover:text-text-primary cursor-pointer">✕</button>
      </div>

      {/* Context pack */}
      {context.data && context.data.sections.length > 0 && (
        <div className="space-y-2">
          <p className="text-xs text-text-secondary font-medium">Context Pack ({context.data.budget_utilization}% of budget)</p>
          {context.data.sections.map((s, i) => (
            <details key={i} className="rounded-md border border-border-subtle p-2" open={i === 0}>
              <summary className="text-xs text-accent cursor-pointer">{s.why}</summary>
              <pre className="mt-2 font-mono text-[11px] text-zinc-300 whitespace-pre-wrap max-h-48 overflow-y-auto">{s.text}</pre>
            </details>
          ))}
        </div>
      )}

      {/* Graph summary */}
      {graph.data && (
        <div className="text-xs text-text-muted font-mono">
          Graph: {graph.data.nodes.length} nodes · {graph.data.edges.length} edges
          <span className="ml-2 text-[10px]">
            {[...new Map(graph.data.edges.map((e) => [e.kind, 1])).keys()].join(', ')}
          </span>
        </div>
      )}

      {/* History via next_ops link */}
      {(context.data?.next_ops?.length ?? 0) > 0 && context.data && (
        <div className="flex flex-wrap gap-2">
          {context.data.next_ops.slice(0, 3).map((op) => (
            <button
              key={op}
              onClick={() => {
                const m = op.match(/path='([^']+)'/)
                if (m) {
                  // TODO(SPEC-06): deep-link to /files?path=<m[1]> history later
                }
              }}
              className="text-[11px] px-2 py-1 rounded bg-accent/10 text-accent hover:bg-accent/20 transition-colors cursor-pointer font-mono"
            >
              {op}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}