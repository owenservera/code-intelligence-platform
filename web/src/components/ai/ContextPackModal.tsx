import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { forensicsApi } from '@/lib/api'
import { Sparkles, Copy, Check, X, Loader2, FileCode2, Cpu, ShieldCheck } from 'lucide-react'

interface ContextPackModalProps {
  isOpen: boolean
  onClose: () => void
  targetPath?: string
  symbolId?: string
}

export function ContextPackModal({
  isOpen,
  onClose,
  targetPath,
  symbolId,
}: ContextPackModalProps) {
  const [maxTokens, setMaxTokens] = useState<number>(4096)
  const [copied, setCopied] = useState(false)

  const packQuery = useQuery({
    queryKey: ['context-pack', targetPath, symbolId, maxTokens],
    queryFn: () => forensicsApi.contextPack({ target_path: targetPath, symbol_id: symbolId, max_tokens: maxTokens }),
    enabled: isOpen,
  })

  if (!isOpen) return null

  const data = packQuery.data
  const tokenCount = data?.token_count ?? 0
  const tokenLimit = data?.token_limit ?? 128000
  const tokenPct = Math.min(100, Math.round((tokenCount / tokenLimit) * 100))

  const handleCopy = () => {
    if (data?.context_pack) {
      navigator.clipboard.writeText(data.context_pack)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4 animate-in fade-in duration-200">
      <div className="w-full max-w-3xl max-h-[85vh] rounded-xl border border-border bg-surface shadow-2xl flex flex-col overflow-hidden">
        {/* Header */}
        <div className="px-5 py-4 border-b border-border flex items-center justify-between bg-surface-raised/40">
          <div className="flex items-center gap-2">
            <div className="p-1.5 rounded-md bg-accent/15 text-accent border border-accent/20">
              <Sparkles className="w-4 h-4" />
            </div>
            <div>
              <h2 className="text-sm font-semibold text-text-primary">AI Context Pack Generator</h2>
              <p className="text-[11px] text-text-muted">Token-budgeted prompt context for Claude, Gemini & GPT-4</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-md text-text-muted hover:text-text-primary hover:bg-surface-raised transition-colors cursor-pointer"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Content Body */}
        <div className="p-5 overflow-y-auto space-y-4 flex-1">
          {/* Controls & Token Gauge */}
          <div className="grid sm:grid-cols-[1fr_auto] gap-4 items-center bg-surface-raised p-3.5 rounded-lg border border-border-subtle">
            <div className="space-y-1.5">
              <div className="flex items-center justify-between text-xs">
                <span className="text-text-muted flex items-center gap-1">
                  <Cpu className="w-3.5 h-3.5 text-accent" />
                  Context Budget Utilization (120K Ceiling)
                </span>
                <span className="font-mono text-text-primary font-semibold">
                  {tokenCount.toLocaleString()} / {tokenLimit.toLocaleString()} tokens ({tokenPct}%)
                </span>
              </div>
              <div className="h-2 rounded-full bg-border overflow-hidden">
                <div
                  className={`h-full rounded-full transition-all ${
                    tokenPct > 80 ? 'bg-error' : tokenPct > 50 ? 'bg-warning' : 'bg-accent'
                  }`}
                  style={{ width: `${Math.max(2, tokenPct)}%` }}
                />
              </div>
            </div>

            <div className="flex items-center gap-2">
              <span className="text-[11px] text-text-muted">Max Budget:</span>
              <select
                value={maxTokens}
                onChange={(e) => setMaxTokens(Number(e.target.value))}
                className="px-2.5 py-1 rounded bg-surface border border-border-subtle text-xs font-mono text-text-primary cursor-pointer"
              >
                <option value={2048}>2,048 tokens</option>
                <option value={4096}>4,096 tokens</option>
                <option value={8192}>8,192 tokens</option>
                <option value={16384}>16,384 tokens</option>
              </select>
            </div>
          </div>

          {targetPath && (
            <div className="flex items-center gap-2 text-xs text-text-muted font-mono bg-accent/5 border border-accent/15 px-3 py-1.5 rounded">
              <FileCode2 className="w-3.5 h-3.5 text-accent" />
              <span>Target File: <strong>{targetPath}</strong></span>
            </div>
          )}

          {/* Context Pack Preview */}
          <div className="space-y-1.5">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-text-secondary uppercase tracking-wider">
                Generated Context Pack
              </span>
              {data && (
                <span className="text-[10px] text-text-muted font-mono">
                  {data.context_pack.length} characters
                </span>
              )}
            </div>

            {packQuery.isLoading ? (
              <div className="h-64 rounded-lg border border-border bg-surface-raised/50 flex items-center justify-center gap-2 text-xs text-text-muted">
                <Loader2 className="w-4 h-4 animate-spin text-accent" />
                Assembling token-budgeted signature map & dependency graph…
              </div>
            ) : (
              <pre className="h-64 rounded-lg border border-border-subtle bg-surface-raised p-3.5 text-[11px] font-mono text-text-primary overflow-auto whitespace-pre-wrap leading-relaxed">
                {data?.context_pack || 'No context pack generated.'}
              </pre>
            )}
          </div>
        </div>

        {/* Footer */}
        <div className="px-5 py-3 border-t border-border bg-surface-raised/40 flex items-center justify-between">
          <div className="flex items-center gap-1.5 text-[11px] text-text-muted">
            <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
            <span>Canonical Anti-Compaction Protection Active</span>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={onClose}
              className="px-3 py-1.5 rounded-lg border border-border hover:bg-surface-raised text-xs text-text-muted hover:text-text-primary transition-colors cursor-pointer"
            >
              Close
            </button>
            <button
              onClick={handleCopy}
              disabled={!data?.context_pack}
              className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg bg-accent text-surface hover:bg-accent-light font-medium text-xs transition-colors cursor-pointer disabled:opacity-50"
            >
              {copied ? <Check className="w-3.5 h-3.5 text-emerald-300" /> : <Copy className="w-3.5 h-3.5" />}
              <span>{copied ? 'Copied to Clipboard!' : 'Copy Context Pack'}</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
