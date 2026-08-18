import { useState } from 'react'
import { Loader2, ArrowLeft } from 'lucide-react'
import type { CommandInfo, CommandParam } from '@/lib/api'
import { cn } from '@/lib/utils'

interface CommandFormProps {
  command: CommandInfo
  submitting?: boolean
  onCancel: () => void
  onSubmit: (params: Record<string, unknown>) => void
}

function defaultFor(p: CommandParam): string | number | boolean {
  if (p.default !== undefined) {
    if (p.type === 'boolean') return Boolean(p.default)
    if (p.type === 'int' || p.type === 'float') return Number(p.default) || 0
    return String(p.default)
  }
  if (p.type === 'boolean') return false
  if (p.type === 'int' || p.type === 'float') return 0
  return ''
}

export function CommandForm({ command, submitting, onCancel, onSubmit }: CommandFormProps) {
  const [values, setValues] = useState<Record<string, string | number | boolean>>(() => {
    const init: Record<string, string | number | boolean> = {}
    for (const p of command.params) init[p.name] = defaultFor(p)
    return init
  })

  const set = (name: string, v: string | number | boolean) =>
    setValues((prev) => ({ ...prev, [name]: v }))

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    onSubmit(values)
  }

  return (
    <form onSubmit={handleSubmit} className="p-3 space-y-3">
      <p className="text-xs text-text-muted">{command.description}</p>
      {command.params.map((p) => (
        <label key={p.name} className="block">
          <span className="flex items-center gap-1.5 text-xs font-mono text-text-primary mb-1">
            {p.name}
            {p.required && <span className="text-accent">*</span>}
          </span>
          {p.type === 'boolean' ? (
            <button
              type="button"
              onClick={() => set(p.name, !values[p.name])}
              className="flex items-center gap-2 text-sm text-text-secondary cursor-pointer"
            >
              <span
                className={cn(
                  'w-8 h-4 rounded-full transition-colors shrink-0',
                  values[p.name] ? 'bg-accent' : 'bg-surface-raised border border-border-subtle',
                )}
              >
                <span
                  className={cn(
                    'block w-3 h-3 rounded-full bg-white transition-transform mt-0.5',
                    values[p.name] ? 'translate-x-4' : 'translate-x-0.5',
                  )}
                />
              </span>
              <span>{values[p.name] ? 'enabled' : 'disabled'}</span>
            </button>
          ) : (
            <input
              type={p.type === 'int' || p.type === 'float' ? 'number' : 'text'}
              step={p.type === 'float' ? 'any' : undefined}
              value={String(values[p.name])}
              placeholder={p.help}
              onChange={(e) => set(p.name, e.target.value)}
              className="w-full px-2.5 py-1.5 rounded-md bg-surface-raised border border-border text-sm text-text-primary outline-none focus:border-accent"
            />
          )}
          {p.help && <span className="block text-[11px] text-text-muted mt-0.5">{p.help}</span>}
        </label>
      ))}

      <div className="flex items-center gap-2 pt-1">
        <button
          type="submit"
          disabled={submitting}
          className={cn(
            'flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm font-medium transition-colors cursor-pointer',
            'bg-accent text-white hover:opacity-90 disabled:opacity-50',
          )}
        >
          {submitting && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
          {submitting ? 'Running…' : 'Execute'}
        </button>
        <button
          type="button"
          onClick={onCancel}
          disabled={submitting}
          className="px-3 py-1.5 rounded-md text-sm text-text-secondary hover:bg-surface-raised transition-colors cursor-pointer"
        >
          Cancel
        </button>
        <span className="ml-auto flex items-center gap-1 text-[10px] text-text-muted font-mono">
          <ArrowLeft className="w-3 h-3" /> esc back
        </span>
      </div>
    </form>
  )
}