import { useQuery } from '@tanstack/react-query'
import {
  settingsApi,
  type ConfigBundle,
  type ConfigKeySchema,
} from '@/lib/api'
import { useMemo, useState } from 'react'
import {
  Loader2, Save, RotateCcw, RefreshCw, ShieldCheck, FileCog,
  SlidersHorizontal, Info, CheckCircle2, AlertTriangle, XCircle,
  Server, Cpu, Wrench, Database, Network, Layers, FolderGit2,
} from 'lucide-react'

const CATEGORIES: { id: string; label: string; icon: React.ComponentType<{ className?: string }>; sections: string[] }[] = [
  { id: 'index', label: 'Index & Paths', icon: Database, sections: ['index', 'summary', 'git'] },
  { id: 'stack', label: 'Stack & Repo Profile', icon: Layers, sections: ['stack', 'profile'] },
  { id: 'embedding', label: 'Embedding', icon: Cpu, sections: ['embed', 'vector', 'rerank'] },
  { id: 'retrieval', label: 'Retrieval', icon: Network, sections: ['retrieval'] },
  { id: 'memory', label: 'Memory', icon: Wrench, sections: ['memory', 'maintain'] },
  { id: 'audit', label: 'Audit', icon: ShieldCheck, sections: ['audit', 'analysis'] },
  { id: 'perf', label: 'Perf', icon: SlidersHorizontal, sections: ['perf', 'performance'] },
  { id: 'daemon', label: 'Daemon & MCP', icon: Server, sections: ['daemon', 'mcp', 'web'] },
  { id: 'logging', label: 'Logging', icon: FileCog, sections: ['logging'] },
]

const SOURCE_BADGE: Record<string, string> = {
  default: 'bg-surface text-text-muted border-border',
  'config.toml': 'bg-accent/10 text-accent border-accent/30',
  profile: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30',
}

interface ValueRenderProps {
  section: string
  key_: string
  schema: ConfigKeySchema
  value: unknown
  onChange: (v: unknown) => void
}

function ValueControl({ section, key_, schema, value, onChange }: ValueRenderProps) {
  const inputCls =
    'w-full rounded-md border border-border bg-app px-2.5 py-1.5 text-sm text-text-primary focus:outline-none focus:border-accent/60'
  if (schema.type === 'bool') {
    return (
      <button
        onClick={() => onChange(!value)}
        className={`h-6 w-11 rounded-full transition-colors ${
          value ? 'bg-accent' : 'bg-surface border border-border'
        }`}
        aria-label={`toggle ${section}.${key_}`}
      >
        <span
          className={`block h-4 w-4 rounded-full bg-white transition-transform ${
            value ? 'translate-x-6' : 'translate-x-1'
          }`}
        />
      </button>
    )
  }
  if (schema.type === 'array') {
    const list = Array.isArray(value) ? value : []
    return (
      <input
        className={inputCls}
        value={list.join(', ')}
        placeholder="comma-separated"
        spellCheck={false}
        onChange={(e) =>
          onChange(
            e.target.value
              .split(',')
              .map((s) => s.trim())
              .filter(Boolean),
          )
        }
      />
    )
  }
  if (schema.choices && schema.choices.length) {
    return (
      <select
        className={inputCls}
        value={String(value ?? '')}
        onChange={(e) => onChange(e.target.value)}
      >
        {schema.choices.map((c) => (
          <option key={c} value={c} className="bg-app">
            {c}
          </option>
        ))}
      </select>
    )
  }
  if (schema.type === 'int' || schema.type === 'float') {
    return (
      <input
        className={inputCls}
        type="number"
        min={schema.min}
        max={schema.max}
        step={schema.type === 'float' ? '0.1' : '1'}
        value={value as number}
        onChange={(e) => {
          const raw = e.target.value
          if (raw === '') return
          const n = schema.type === 'float' ? parseFloat(raw) : parseInt(raw, 10)
          if (!Number.isNaN(n)) onChange(n)
        }}
      />
    )
  }
  return (
    <input
      className={inputCls}
      value={String(value ?? '')}
      spellCheck={false}
      onChange={(e) => onChange(e.target.value)}
    />
  )
}

export function SettingsView() {
  const [draft, setDraft] = useState<Record<string, Record<string, unknown>>>({})
  const [dirty, setDirty] = useState(false)
  const [busy, setBusy] = useState<string | null>(null)
  const [notice, setNotice] = useState<{ kind: 'ok' | 'warn' | 'err'; text: string } | null>(null)

  const schemaQ = useQuery({ queryKey: ['config-schema'], queryFn: settingsApi.schema })
  const bundleQ = useQuery({ queryKey: ['config-bundle'], queryFn: settingsApi.bundle })
  const envQ = useQuery({ queryKey: ['config-env'], queryFn: settingsApi.env })

  const bundle = bundleQ.data
  const schema = schemaQ.data?.schema ?? {}

  // Seed draft from effective config on first load (or when bundle invalidates)
  const effective = bundle?.effective ?? {}
  const seeded = useMemo(() => {
    const out: Record<string, Record<string, unknown>> = {}
    for (const section of Object.keys(effective)) {
      if (typeof effective[section] !== 'object' || effective[section] === null) continue
      out[section] = { ...(effective[section] as Record<string, unknown>) }
    }
    return out
  }, [bundleQ.dataUpdatedAt, effective])

  const active = dirty ? draft : seeded

  const setValue = (section: string, key_: string, v: unknown) => {
    setDraft((prev) => {
      const next = { ...prev, [section]: { ...prev[section], [key_]: v } }
      return next
    })
    setDirty(true)
  }

  const changed: Record<string, Record<string, unknown>> = useMemo(() => {
    const out: Record<string, Record<string, unknown>> = {}
    for (const section of Object.keys(active)) {
      const effSection = effective[section] ?? {}
      for (const [k, v] of Object.entries(active[section] ?? {})) {
        if (JSON.stringify(effSection[k]) !== JSON.stringify(v)) {
          out[section] = { ...out[section], [k]: v }
        }
      }
    }
    return out
  }, [active, effective])

  const changeCount = Object.values(changed).reduce((n, s) => n + Object.keys(s).length, 0)

  const resetAll = () => {
    setDraft({})
    setDirty(false)
    setNotice(null)
  }

  const validate = async () => {
    setBusy('validate')
    setNotice(null)
    try {
      const r = await settingsApi.validate(changed)
      setNotice(
        r.ok
          ? { kind: 'ok', text: 'Validation passed — types and ranges are valid.' }
          : { kind: 'warn', text: `${r.errors.length} issue(s): ${r.errors.slice(0, 5).join('; ')}` },
      )
    } catch (e) {
      setNotice({ kind: 'err', text: `Validate failed: ${String(e)}` })
    } finally {
      setBusy(null)
    }
  }

  const save = async () => {
    setBusy('save')
    setNotice(null)
    try {
      const r = await settingsApi.save(changed)
      if (!r.ok) {
        setNotice({ kind: 'err', text: `Save rejected: ${(r.errors ?? []).slice(0, 5).join('; ')}` })
      } else {
        setNotice({ kind: 'ok', text: `Saved ${r.written_keys.length} key(s) → .cip/config.toml (backup written).` })
        setDraft({})
        setDirty(false)
        await Promise.allSettled([bundleQ.refetch(), schemaQ.refetch()])
      }
    } catch (e) {
      setNotice({ kind: 'err', text: `Save failed: ${String(e)}` })
    } finally {
      setBusy(null)
    }
  }

  const resetKey = async (section: string, key_: string) => {
    setBusy('reset')
    setNotice(null)
    try {
      await settingsApi.reset(section, [key_])
      setDraft((prev) => {
        const nextSection = { ...prev[section] }
        delete nextSection[key_ as keyof typeof nextSection]
        return { ...prev, [section]: nextSection }
      })
      setNotice({ kind: 'ok', text: `Reset ${section}.${key_} (override removed, default restored).` })
      await bundleQ.refetch()
    } catch (e) {
      setNotice({ kind: 'err', text: `Reset failed: ${String(e)}` })
    } finally {
      setBusy(null)
    }
  }

  const reload = async () => {
    setBusy('reload')
    setNotice(null)
    try {
      const r = await settingsApi.reload()
      setNotice({ kind: 'ok', text: `Reload job ${r.job_id} started — caches cleared, config re-derived.` })
    } catch (e) {
      setNotice({ kind: 'err', text: `Reload failed: ${String(e)}` })
    } finally {
      setBusy(null)
    }
  }

  const loading = schemaQ.isLoading || bundleQ.isLoading || envQ.isLoading

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      <div className="flex items-end justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-2xl font-semibold text-text-primary mb-1">Settings &amp; Config</h1>
          <p className="text-text-muted text-sm">
            Edit supported sections → validate → save writes <code className="text-accent">.cip/config.toml</code> with a
            backup. Source badges show where each value comes from.
          </p>
        </div>
        <div className="flex items-center gap-2">
          {dirty && (
            <button
              onClick={resetAll}
              disabled={!!busy}
              className="flex items-center gap-2 rounded-lg border border-border bg-surface px-3 py-1.5 text-xs font-medium text-text-muted hover:border-accent/50 transition-colors cursor-pointer disabled:opacity-50"
            >
              <RotateCcw className="w-3.5 h-3.5" />
              Discard
            </button>
          )}
          <button
            onClick={validate}
            disabled={!!busy || changeCount === 0}
            className="flex items-center gap-2 rounded-lg border border-border bg-surface px-3 py-1.5 text-xs font-medium text-text-primary hover:border-accent/50 transition-colors cursor-pointer disabled:opacity-50"
          >
            {busy === 'validate' ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <CheckCircle2 className="w-3.5 h-3.5 text-accent" />}
            Validate
          </button>
          <button
            onClick={save}
            disabled={!!busy || changeCount === 0}
            className="flex items-center gap-2 rounded-lg bg-accent px-3 py-1.5 text-xs font-semibold text-white hover:bg-accent/90 transition-colors cursor-pointer disabled:opacity-50"
          >
            {busy === 'save' ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Save className="w-3.5 h-3.5" />}
            Save ({changeCount})
          </button>
          <button
            onClick={reload}
            disabled={!!busy}
            className="flex items-center gap-2 rounded-lg border border-border bg-surface px-3 py-1.5 text-xs font-medium text-text-primary hover:border-accent/50 transition-colors cursor-pointer disabled:opacity-50"
          >
            {busy === 'reload' ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <RefreshCw className="w-3.5 h-3.5 text-accent" />}
            Reload
          </button>
        </div>
      </div>

      {notice && (
        <div
          className={`flex items-start gap-2 rounded-lg border px-3 py-2.5 text-sm ${
            notice.kind === 'ok'
              ? 'border-emerald-500/30 bg-emerald-500/10 text-emerald-300'
              : notice.kind === 'warn'
                ? 'border-amber-500/30 bg-amber-500/10 text-amber-300'
                : 'border-error/40 bg-error/10 text-error'
          }`}
        >
          {notice.kind === 'ok' ? (
            <CheckCircle2 className="w-4 h-4 shrink-0 mt-0.5" />
          ) : notice.kind === 'warn' ? (
            <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
          ) : (
            <XCircle className="w-4 h-4 shrink-0 mt-0.5" />
          )}
          <span>{notice.text}</span>
        </div>
      )}

      {loading && (
        <div className="flex items-center justify-center py-16">
          <Loader2 className="w-6 h-6 animate-spin text-accent" />
        </div>
      )}

      {!loading && bundle && (
        <>
          {/* Schema/version banner */}
          {(schemaQ.data?.live_schema_version != null || schemaQ.data?.declared_schema_version != null) && (
            <div className="rounded-lg border border-border bg-surface/50 px-4 py-2.5 flex items-center gap-2 text-xs text-text-muted">
              <Info className="w-3.5 h-3.5 text-accent shrink-0" />
              <span>
                Live DB schema v{schemaQ.data?.live_schema_version ?? '?'}
                <span className="text-text-muted/60">
                  {' '}
                  (config meta declares v{schemaQ.data?.declared_schema_version ?? '?'} — trust the live value, CORE-40)
                </span>
              </span>
            </div>
          )}

          {/* Category sections */}
          {CATEGORIES.filter((cat) => cat.sections.some((s) => schema[s])).map((cat) => {
            const Icon = cat.icon
            return (
              <div key={cat.id} className="rounded-xl border border-border bg-surface">
                <div className="flex items-center gap-2 px-4 py-3 border-b border-border">
                  <Icon className="w-4 h-4 text-accent" />
                  <h2 className="text-sm font-semibold text-text-primary">{cat.label}</h2>
                </div>
                <div className="divide-y divide-border">
                  {cat.sections
                    .filter((s) => schema[s])
                    .map((section) => (
                      <SectionCard
                        key={section}
                        section={section}
                        schemaEntries={schema[section]}
                        values={active[section] ?? {}}
                        defaults={bundle.defaults[section] ?? {}}
                        dirty={!!dirty || Object.keys(changed[section] ?? {}).length > 0}
                        onSet={setValue}
                        onReset={(k) => resetKey(section, k)}
                      />
                    ))}
                </div>
              </div>
            )
          })}

          {/* Repo Profile, Three-way bundle + env */}
          <div className="grid md:grid-cols-3 gap-6">
            <RepoProfilePanel bundle={bundle} />
            <ConfigFilePanel bundle={bundle} />
            <EnvPanel env={envQ.data?.env ?? {}} liveSchema={envQ.data?.live_schema_version ?? null} />
          </div>
        </>
      )}
    </div>
  )
}

function RepoProfilePanel({ bundle }: { bundle: ConfigBundle }) {
  const profile = bundle.detected_profile
  const effective = bundle.effective
  const indexInclude = (effective?.index?.include as string[]) || []
  const indexExclude = (effective?.index?.exclude as string[]) || []
  const stack = (effective?.stack as Record<string, unknown>) || {}

  return (
    <div className="rounded-xl border border-border bg-surface flex flex-col">
      <div className="px-4 py-3 border-b border-border">
        <h2 className="text-sm font-semibold text-text-primary flex items-center gap-2">
          <FolderGit2 className="w-4 h-4 text-accent" />
          Active Repo Profile
        </h2>
      </div>
      <div className="p-4 space-y-3 text-xs flex-1">
        <div className="flex items-center justify-between">
          <span className="text-text-muted">Detected Type</span>
          <span className="font-mono text-accent font-medium bg-accent/10 px-2 py-0.5 rounded border border-accent/20">
            {profile?.repo_type ?? 'generic'}
          </span>
        </div>

        {profile?.profile_dir && (
          <div className="space-y-1">
            <span className="text-text-muted block text-[11px]">Profile Source</span>
            <span className="font-mono text-[10px] text-text-secondary bg-surface-raised px-2 py-1 rounded block truncate border border-border-subtle" title={profile.profile_dir}>
              {profile.profile_dir}
            </span>
          </div>
        )}

        {profile?.profile_files && profile.profile_files.length > 0 && (
          <div className="space-y-1">
            <span className="text-text-muted block text-[11px]">Loaded TOMLs</span>
            <div className="flex flex-wrap gap-1">
              {profile.profile_files.map((f) => (
                <span key={f} className="font-mono text-[10px] bg-surface-raised text-text-secondary px-1.5 py-0.5 rounded border border-border-subtle">
                  {f}
                </span>
              ))}
            </div>
          </div>
        )}

        {indexInclude.length > 0 && (
          <div className="space-y-1 pt-1 border-t border-border-subtle">
            <span className="text-text-muted block text-[11px]">Included Roots ({indexInclude.length})</span>
            <div className="flex flex-wrap gap-1 max-h-20 overflow-y-auto">
              {indexInclude.map((inc) => (
                <span key={inc} className="font-mono text-[10px] bg-emerald-500/10 text-emerald-300 px-1.5 py-0.5 rounded border border-emerald-500/20">
                  +{inc}
                </span>
              ))}
            </div>
          </div>
        )}

        {indexExclude.length > 0 && (
          <div className="space-y-1 pt-1 border-t border-border-subtle">
            <span className="text-text-muted block text-[11px]">Excluded Patterns ({indexExclude.length})</span>
            <div className="flex flex-wrap gap-1 max-h-20 overflow-y-auto">
              {indexExclude.slice(0, 6).map((exc) => (
                <span key={exc} className="font-mono text-[10px] bg-surface-raised text-text-muted px-1.5 py-0.5 rounded border border-border-subtle">
                  -{exc}
                </span>
              ))}
              {indexExclude.length > 6 && (
                <span className="text-[10px] text-text-muted self-center">+{indexExclude.length - 6} more</span>
              )}
            </div>
          </div>
        )}

        {Object.keys(stack).length > 0 && (
          <div className="space-y-1 pt-1 border-t border-border-subtle">
            <span className="text-text-muted block text-[11px]">Stack Features</span>
            <div className="flex flex-wrap gap-1">
              {Object.entries(stack).map(([k, v]) => (
                <span key={k} className="font-mono text-[10px] bg-surface-raised text-text-secondary px-1.5 py-0.5 rounded border border-border-subtle">
                  {k}: {String(v)}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

function SectionCard({
  section,
  schemaEntries,
  values,
  defaults,
  dirty,
  onSet,
  onReset,
}: {
  section: string
  schemaEntries: Record<string, ConfigKeySchema>
  values: Record<string, unknown>
  defaults: Record<string, unknown>
  dirty: boolean
  onSet: (section: string, k: string, v: unknown) => void
  onReset: (k: string) => void
}) {
  return (
    <div className={`px-4 py-3 ${dirty ? 'bg-accent/[0.03]' : ''}`}>
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs font-mono text-accent">[{section}]</span>
        {dirty && <span className="text-[10px] uppercase tracking-wide text-amber-400">edited</span>}
      </div>
      <div className="space-y-3">
        {Object.entries(schemaEntries).map(([key, s]) => {
          const val = values[key] ?? s.default
          const changedHere = valsDiffer(values[key], defaults[key])
          return (
            <div key={key} className="grid grid-cols-[220px_1fr] gap-3 items-start">
              <div className="min-w-0">
                <div className="flex items-center gap-1.5 group">
                  <span className="text-sm font-medium text-text-primary truncate">{key}</span>
                  <span className={`rounded-md border px-1.5 py-px text-[9px] font-medium ${SOURCE_BADGE[s.source] ?? SOURCE_BADGE.default}`}>
                    {s.source}
                  </span>
                  {changedHere && (
                    <span className="w-1.5 h-1.5 rounded-full bg-accent shrink-0" title="differs from default" />
                  )}
                </div>
                <p className="text-[11px] text-text-muted/80 leading-snug">{s.desc}</p>
              </div>
              <div className="flex items-start justify-end gap-2">
                <div className="flex-1 max-w-[260px]">
                  <ValueControl section={section} key_={key} schema={s} value={val} onChange={(v) => onSet(section, key, v)} />
                </div>
                {s.source !== 'default' && (
                  <button
                    onClick={() => onReset(key)}
                    title="Restore default"
                    className="mt-1 rounded-md p-1 text-text-muted hover:text-accent hover:bg-accent/10 transition-colors cursor-pointer"
                  >
                    <RotateCcw className="w-3.5 h-3.5" />
                  </button>
                )}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

function valsDiffer(a: unknown, b: unknown): boolean {
  if (a === b) return false
  if (Array.isArray(a) && Array.isArray(b)) {
    return JSON.stringify([...a].sort()) !== JSON.stringify([...b].sort())
  }
  return true
}

function ConfigFilePanel({ bundle }: { bundle: ConfigBundle }) {
  const fileSections = Object.entries(bundle.file)
  return (
    <div className="rounded-xl border border-border bg-surface">
      <div className="px-4 py-3 border-b border-border">
        <h2 className="text-sm font-semibold text-text-primary flex items-center gap-2">
          <FileCog className="w-4 h-4 text-accent" />
          .cip/config.toml <span className="text-[10px] text-text-muted font-normal">({fileSections.length} sections on disk)</span>
        </h2>
      </div>
      {fileSections.length === 0 ? (
        <p className="px-4 py-4 text-xs text-text-muted">
          No local override file yet. Saving keys creates <code className="text-accent">.cip/config.toml</code>.
        </p>
      ) : (
        <div className="max-h-72 overflow-auto px-4 py-3 space-y-2 font-mono text-[11px]">
          {fileSections.map(([section, kv]) => (
            <div key={section}>
              <div className="text-accent">[{section}]</div>
              {Object.entries(kv as Record<string, unknown>).map(([k, v]) => (
                <div key={k} className="pl-3 text-text-muted">
                  <span className="text-text-primary">{k}</span> = {JSON.stringify(v)}
                </div>
              ))}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

function EnvPanel({ env, liveSchema }: { env: Record<string, string>; liveSchema: number | null }) {
  return (
    <div className="rounded-xl border border-border bg-surface">
      <div className="px-4 py-3 border-b border-border">
        <h2 className="text-sm font-semibold text-text-primary flex items-center gap-2">
          <Server className="w-4 h-4 text-accent" />
          Environment
        </h2>
      </div>
      <div className="px-4 py-3 space-y-1.5">
        {Object.entries(env).map(([k, v]) => (
          <div key={k} className="grid grid-cols-[150px_1fr] gap-2 text-[11px]">
            <span className="text-accent font-mono truncate">{k}</span>
            <span className="text-text-muted font-mono break-all">{v}</span>
          </div>
        ))}
        {liveSchema != null && (
          <div className="grid grid-cols-[150px_1fr] gap-2 text-[11px] pt-1 border-t border-border">
            <span className="text-accent font-mono">DB schema</span>
            <span className="text-text-muted font-mono">v{liveSchema}</span>
          </div>
        )}
      </div>
    </div>
  )
}