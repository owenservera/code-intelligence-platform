import { useQuery } from '@tanstack/react-query'
import {
  exportApi,
  type ExportFormat,
  type ExportKind,
} from '@/lib/api'
import { useState } from 'react'
import {
  Download, FileJson, FileText, Network, Server, Database,
  Loader2, Search, TerminalSquare, ShieldCheck, ChevronDown, ChevronRight,
} from 'lucide-react'

const DOWNLOADS: { kind: ExportKind; label: string; blurb: string }[] = [
  { kind: 'repo', label: 'Full index', blurb: 'files · symbols · edges · summaries · signals' },
  { kind: 'findings', label: 'Findings', blurb: 'open audit findings (severity/rule/path/message)' },
  { kind: 'index', label: 'Index stats', blurb: 'overview payload — counts, gate, freshness' },
]

export function ExportView() {
  const statusQ = useQuery({ queryKey: ['export-status'], queryFn: exportApi.status })
  const toolsQ = useQuery({ queryKey: ['export-tools'], queryFn: exportApi.tools })

  const [searchQ, setSearchQ] = useState('')
  const [ingestKind, setIngestKind] = useState<'vitest' | 'jest' | 'pytest' | 'tsc' | 'generic'>('tsc')
  const [ingestText, setIngestText] = useState('')
  const [notice, setNotice] = useState<{ kind: 'ok' | 'err'; text: string } | null>(null)
  const [busy, setBusy] = useState<string | null>(null)
  const [openTool, setOpenTool] = useState<string | null>(null)

  const status = statusQ.data
  const tools = toolsQ.data?.tools ?? []

  const ingest = async () => {
    if (!ingestText.trim()) return
    setBusy('ingest')
    setNotice(null)
    try {
      const r = await exportApi.ingest(ingestKind, ingestText)
      setNotice({ kind: 'ok', text: `Parsed ${r.ingested} signal(s) (kind: ${r.kind}) — now visible in Visualize → Signals and exports.` })
      await statusQ.refetch()
    } catch (e) {
      setNotice({ kind: 'err', text: `Ingest failed: ${String(e)}` })
    } finally {
      setBusy(null)
    }
  }

  const runVerify = async (typecheck: boolean, lint: boolean) => {
    setBusy(`verify:${typecheck}:${lint}`)
    setNotice(null)
    try {
      const r = await exportApi.verify(typecheck, lint)
      setNotice({
        kind: 'ok',
        text: `Verification gate job ${r.job_id} started (typecheck=${typecheck ? 'on' : 'off'}, lint=${lint ? 'on' : 'off'}). Result streams to the Console log.`,
      })
    } catch (e) {
      setNotice({ kind: 'err', text: `Verify failed: ${String(e)}` })
    } finally {
      setBusy(null)
    }
  }

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-text-primary mb-1">Export &amp; Integration</h1>
        <p className="text-text-muted text-sm">
          Live downloads of CIP intelligence (JSON / Markdown), MCP + daemon integration cards,
          the MCP tools schema, runtime signal ingestion, and the verification gate. No index writes.
        </p>
      </div>

      {notice && (
        <div
          className={`flex items-start gap-2 rounded-lg border px-3 py-2.5 text-sm ${
            notice.kind === 'ok'
              ? 'border-emerald-500/30 bg-emerald-500/10 text-emerald-300'
              : 'border-error/40 bg-error/10 text-error'
          }`}
        >
          {notice.kind === 'ok' ? <ShieldCheck className="w-4 h-4 shrink-0 mt-0.5" /> : null}
          <span>{notice.text}</span>
        </div>
      )}

      {statusQ.isLoading ? (
        <div className="flex items-center justify-center py-16">
          <Loader2 className="w-6 h-6 animate-spin text-accent" />
        </div>
      ) : (
        <>
          {/* Integration status cards */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <StatusCard
              icon={<Network className="w-4 h-4" />}
              title="MCP server"
              ok={status?.mcp.reachable}
              detail={status ? (status.mcp.reachable ? `listening on :${status.mcp.port}` : `not reachable on :${status.mcp.port}`) : ''}
            />
            <StatusCard
              icon={<Server className="w-4 h-4" />}
              title="CIP daemon"
              ok={status?.daemon.reachable}
              detail={status ? (status.daemon.reachable ? `listening on :${status.daemon.port}` : `not running on :${status.daemon.port}`) : ''}
            />
            <StatusCard
              icon={<Database className="w-4 h-4" />}
              title="Index"
              ok={status?.index.ready}
              detail={
                status ? `${status.index.files} files · ${status.index.symbols} symbols · ${status.index.signals} signals` : ''
              }
            />
          </div>

          {/* Downloads */}
          <div className="rounded-xl border border-border bg-surface">
            <div className="px-4 py-3 border-b border-border">
              <h2 className="text-sm font-semibold text-text-primary flex items-center gap-2">
                <Download className="w-4 h-4 text-accent" />
                Export downloads
              </h2>
            </div>
            <div className="divide-y divide-border">
              {DOWNLOADS.map(({ kind, label, blurb }) => (
                <div key={kind} className="px-4 py-3 flex items-center justify-between flex-wrap gap-3">
                  <div>
                    <div className="text-sm font-medium text-text-primary">{label}</div>
                    <div className="text-[11px] text-text-muted">{blurb}</div>
                  </div>
                  <div className="flex items-center gap-2">
                    <a
                      href={exportApi.downloadUrl(kind, 'json')}
                      className="flex items-center gap-1.5 rounded-md border border-border bg-app px-2.5 py-1.5 text-xs text-text-primary hover:border-accent/50 transition-colors"
                    >
                      <FileJson className="w-3.5 h-3.5 text-accent" />
                      JSON
                    </a>
                    <a
                      href={exportApi.downloadUrl(kind, 'markdown')}
                      className="flex items-center gap-1.5 rounded-md border border-border bg-app px-2.5 py-1.5 text-xs text-text-primary hover:border-accent/50 transition-colors"
                    >
                      <FileText className="w-3.5 h-3.5 text-accent" />
                      Markdown
                    </a>
                  </div>
                </div>
              ))}

              {/* Search export */}
              <div className="px-4 py-3">
                <div className="text-sm font-medium text-text-primary mb-1">Search results export</div>
                <div className="flex items-center gap-2 flex-wrap">
                  <div className="relative flex-1 min-w-[220px]">
                    <Search className="w-3.5 h-3.5 absolute left-2.5 top-1/2 -translate-y-1/2 text-text-muted" />
                    <input
                      value={searchQ}
                      onChange={(e) => setSearchQ(e.target.value)}
                      placeholder="query (lexical only — no embedding model load)"
                      spellCheck={false}
                      className="w-full rounded-md border border-border bg-app pl-8 pr-2.5 py-1.5 text-sm text-text-primary focus:outline-none focus:border-accent/60"
                    />
                  </div>
                  {(['json', 'markdown'] as ExportFormat[]).map((f) => (
                    <a
                      key={f}
                      href={searchQ.trim() ? exportApi.downloadUrl('search', f, searchQ.trim()) : undefined}
                      onClick={(e) => {
                        if (!searchQ.trim()) {
                          e.preventDefault()
                          setNotice({ kind: 'err', text: 'Enter a query first.' })
                        } else {
                          setNotice(null)
                        }
                      }}
                      className={`flex items-center gap-1.5 rounded-md border px-2.5 py-1.5 text-xs transition-colors ${
                        searchQ.trim()
                          ? 'border-border bg-app text-text-primary hover:border-accent/50'
                          : 'border-border bg-app text-text-muted cursor-not-allowed'
                      }`}
                    >
                      {f === 'json' ? <FileJson className="w-3.5 h-3.5 text-accent" /> : <FileText className="w-3.5 h-3.5 text-accent" />}
                      {f}
                    </a>
                  ))}
                </div>
              </div>
            </div>
          </div>

          {/* Signal ingest */}
          <div className="rounded-xl border border-border bg-surface">
            <div className="px-4 py-3 border-b border-border">
              <h2 className="text-sm font-semibold text-text-primary flex items-center gap-2">
                <TerminalSquare className="w-4 h-4 text-accent" />
                Ingest runtime signals
              </h2>
            </div>
            <div className="px-4 py-3 space-y-3">
              <div className="flex items-center gap-2">
                <span className="text-xs text-text-muted">Kind:</span>
                {(['vitest', 'jest', 'pytest', 'tsc', 'generic'] as const).map((k) => (
                  <button
                    key={k}
                    onClick={() => setIngestKind(k)}
                    className={`rounded-md px-2.5 py-1 text-[11px] font-medium transition-colors cursor-pointer ${
                      ingestKind === k
                        ? 'bg-accent text-white'
                        : 'bg-app border border-border text-text-muted hover:border-accent/50'
                    }`}
                  >
                    {k}
                  </button>
                ))}
              </div>
              <textarea
                value={ingestText}
                onChange={(e) => setIngestText(e.target.value)}
                rows={5}
                placeholder={
                  ingestKind === 'tsc'
                    ? 'Paste tsc output, e.g.\nsrc/a.ts(3,5): error TS2322: Type mismatch'
                    : ingestKind === 'pytest'
                      ? 'Paste JUnit XML (<testsuite>...</testsuite>)'
                      : ingestKind === 'generic'
                        ? 'Paste JSON: {"events":[{"kind":"...","path":"...","name":"...","payload":{}}]}'
                        : `Paste ${ingestKind} JSON report (testResults → assertionResults)`
                }
                spellCheck={false}
                className="w-full rounded-md border border-border bg-app px-3 py-2 text-xs font-mono text-text-primary focus:outline-none focus:border-accent/60 resize-y min-h-[80px]"
              />
              <div className="flex items-center justify-between">
                <span className="text-[11px] text-text-muted">Stable ids prevent duplicates (CORE-46). Parsed on server by runtime_adapters.</span>
                <button
                  onClick={ingest}
                  disabled={busy === 'ingest' || !ingestText.trim()}
                  className="flex items-center gap-2 rounded-lg bg-accent px-3 py-1.5 text-xs font-semibold text-white hover:bg-accent/90 transition-colors cursor-pointer disabled:opacity-50"
                >
                  {busy === 'ingest' ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Download className="w-3.5 h-3.5" />}
                  Ingest
                </button>
              </div>
            </div>
          </div>

          {/* Verification gate */}
          <div className="rounded-xl border border-border bg-surface">
            <div className="px-4 py-3 border-b border-border">
              <h2 className="text-sm font-semibold text-text-primary flex items-center gap-2">
                <ShieldCheck className="w-4 h-4 text-accent" />
                Verification gate
              </h2>
            </div>
            <div className="px-4 py-3 flex items-center justify-between flex-wrap gap-3">
              <p className="text-[11px] text-text-muted max-w-md">
                Broken tests are always checked. Optionally add <code className="text-accent">tsc --noEmit</code> and
                <code className="text-accent"> eslint</code>. Critical audit findings are included. Runs asynchronously;
                result event appears in the Console log.
              </p>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => runVerify(false, false)}
                  disabled={busy?.startsWith('verify')}
                  className="flex items-center gap-2 rounded-lg border border-border bg-app px-3 py-1.5 text-xs font-medium text-text-primary hover:border-accent/50 transition-colors cursor-pointer disabled:opacity-50"
                >
                  {busy === 'verify:false:false' ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <ShieldCheck className="w-3.5 h-3.5 text-accent" />}
                  Gate (tests + audit)
                </button>
                <button
                  onClick={() => runVerify(true, true)}
                  disabled={busy?.startsWith('verify')}
                  className="flex items-center gap-2 rounded-lg bg-accent px-3 py-1.5 text-xs font-semibold text-white hover:bg-accent/90 transition-colors cursor-pointer disabled:opacity-50"
                >
                  {busy === 'verify:true:true' ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <ShieldCheck className="w-3.5 h-3.5" />}
                  Full gate
                </button>
              </div>
            </div>
          </div>

          {/* Tools schema */}
          <div className="rounded-xl border border-border bg-surface">
            <div className="px-4 py-3 border-b border-border">
              <h2 className="text-sm font-semibold text-text-primary flex items-center gap-2">
                <Server className="w-4 h-4 text-accent" />
                MCP tools schema <span className="text-[10px] text-text-muted font-normal">({toolsQ.isLoading ? '…' : `${tools.length} tools`})</span>
              </h2>
            </div>
            {toolsQ.isLoading ? (
              <div className="px-4 py-6 flex justify-center">
                <Loader2 className="w-5 h-5 animate-spin text-accent" />
              </div>
            ) : (
              <div className="divide-y divide-border">
                {tools.slice(0, 120).map((t) => (
                  <div key={t.name} className="px-4 py-2.5">
                    <button
                      onClick={() => setOpenTool(openTool === t.name ? null : t.name)}
                      className="w-full flex items-center justify-between gap-2 cursor-pointer"
                    >
                      <span className="text-sm text-text-primary font-mono">
                        {t.name}
                        <span className="ml-2 text-[10px] text-text-muted font-sans">{t.category}</span>
                      </span>
                      <span className="flex items-center gap-2">
                        <span className="text-[10px] text-text-muted">{t.params.length} param(s)</span>
                        {openTool === t.name ? (
                          <ChevronDown className="w-3.5 h-3.5 text-text-muted" />
                        ) : (
                          <ChevronRight className="w-3.5 h-3.5 text-text-muted" />
                        )}
                      </span>
                    </button>
                    {openTool === t.name && (
                      <div className="mt-2 pl-0 space-y-1.5">
                        <p className="text-[11px] text-text-muted">{t.description || '—'}</p>
                        <p className="text-[11px] text-text-muted">
                          <span className="text-accent">returns:</span> <code>{t.returns}</code>
                          <span className="text-accent"> · invoke:</span> <code>{t.invoke}</code>
                        </p>
                        {t.params.length > 0 && (
                          <table className="w-full text-[11px]">
                            <thead>
                              <tr className="text-text-muted text-left">
                                <th className="py-1 pr-3">param</th>
                                <th className="py-1 pr-3">type</th>
                                <th className="py-1 pr-3">required</th>
                                <th className="py-1">help</th>
                              </tr>
                            </thead>
                            <tbody className="font-mono">
                              {t.params.map((p) => (
                                <tr key={p.name} className="text-text-primary">
                                  <td className="py-0.5 pr-3 text-accent">{p.name}</td>
                                  <td className="py-0.5 pr-3 text-text-muted">{p.type}</td>
                                  <td className="py-0.5 pr-3 text-text-muted">{p.required ? 'yes' : 'no'}</td>
                                  <td className="py-0.5 text-text-muted">{p.help || '—'}</td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        )}
                      </div>
                    )}
                  </div>
                ))}
                {tools.length > 120 && (
                  <p className="px-4 py-2 text-[11px] text-text-muted">
                    Showing first 120 of {tools.length} tools.
                  </p>
                )}
              </div>
            )}
          </div>
        </>
      )}
    </div>
  )
}

function StatusCard({ icon, title, ok, detail }: {
  icon: React.ReactNode
  title: string
  ok?: boolean
  detail: string
}) {
  return (
    <div className="rounded-xl border border-border bg-surface p-4">
      <div className="flex items-center justify-between">
        <span className={`w-8 h-8 rounded-lg flex items-center justify-center ${
          ok === undefined ? 'bg-surface text-text-muted' : ok ? 'bg-emerald-500/10 text-emerald-400' : 'bg-error/10 text-error'
        }`}>
          {icon}
        </span>
        <span className={`h-2.5 w-2.5 rounded-full ${
          ok === undefined ? 'bg-text-muted/50' : ok ? 'bg-emerald-500' : 'bg-error'
        }`} />
      </div>
      <div className="mt-3 text-sm font-medium text-text-primary">{title}</div>
      <div className="text-[11px] text-text-muted mt-0.5 break-words">{detail}</div>
    </div>
  )
}