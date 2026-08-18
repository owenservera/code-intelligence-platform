import { useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useVirtualizer } from '@tanstack/react-virtual'
import {
  asyncDataLoaderFeature,
  hotkeysCoreFeature,
  searchFeature,
  selectionFeature,
} from '@headless-tree/core'
import { useTree } from '@headless-tree/react'
import { fileApi } from '@/lib/api'
import { useAppStore } from '@/stores/app'
import { ChevronRight, FileCode, Folder, FolderOpen, Search } from 'lucide-react'

// PLAN-08 T8.1/T8.3: VS Code-style repo explorer built on @headless-tree (spike
// decision) + @tanstack/react-virtual. Backed by lazy GET /api/tree?path= (one
// request per expanded dir, SPEC-16 §3). Read-only: files open the deep panel
// via navigate('/files?path='), never an inline editor.

export interface TreeNode {
  path: string
  name: string
  isDir: boolean
  status?: string
}

const GIT_GLYPH: Record<string, { label: string; cls: string }> = {
  M: { label: 'M', cls: 'text-amber-400' },
  A: { label: 'A', cls: 'text-success' },
  '?': { label: '?', cls: 'text-accent' },
}

// Shared item-data resolver: returns the cached node for a path, falling back to
// a derived placeholder (directories expand lazily; files resolve once their
// parent dir has been fetched).
function treeIdToData(
  itemId: string,
  cache: Map<string, Record<string, TreeNode>>,
  projectName: string,
): TreeNode {
  if (itemId === '') {
    return { path: '', name: projectName, isDir: true }
  }
  for (const nodes of cache.values()) {
    const n = nodes[itemId]
    if (n) return n
  }
  const name = itemId.split('/').pop() ?? itemId
  return { path: itemId, name, isDir: true }
}

export function RepoExplorer() {
  const navigate = useNavigate()
  const [params] = useSearchParams()
  const routePath = params.get('path') ?? null
  const activeProject = useAppStore((s) => s.activeProject)
  const projects = useAppStore((s) => s.projects)
  const setActivePath = useAppStore((s) => s.setActivePath)
  const setExpanded = useAppStore((s) => s.setExpanded)
  const setLoadingDir = useAppStore((s) => s.setLoadingDir)
  const fileChangeEpoch = useAppStore((s) => s.fileChangeEpoch)
  const lastChangedPath = useAppStore((s) => s.lastChangedPath)
  const [filter, setFilter] = useState('')
  const scrollRef = useRef<HTMLDivElement>(null)
  const projectName = useMemo(
    () => projects.find((p) => p.id === activeProject)?.name ?? 'repo',
    [projects, activeProject],
  )

  // Data cache: path ('' = root) → nodes by path. Filled lazily as dirs expand;
  // asyncDataLoaderFeature reads tree.getConfig().dataLoader on every call, so
  // the closure always sees the latest cached + fetch functions.
  const cacheRef = useRef<Map<string, Record<string, TreeNode>>>(new Map())

  const fetchListing = async (path: string): Promise<TreeNode[]> => {
    const cached = cacheRef.current.get(path)
    if (cached) return Object.values(cached)
    const listing = await fileApi.tree(path)
    const nodes: TreeNode[] = [
      ...listing.dirs.map((d) => ({ path: d.path, name: d.name, isDir: true })),
      ...listing.files.map((f) => ({ path: f.path, name: f.name, isDir: false, status: f.status })),
    ]
    const byPath: Record<string, TreeNode> = {}
    for (const n of nodes) byPath[n.path] = n
    cacheRef.current.set(path, byPath)
    return nodes
  }

  const tree = useTree<TreeNode>({
    rootItemId: '',
    getItemName: (item) => item.getItemData()?.name ?? item.getId(),
    isItemFolder: (item) => item.getItemData()?.isDir === true,
    dataLoader: {
      getItem: (itemId) => treeIdToData(itemId, cacheRef.current, projectName),
      getChildrenWithData: async (itemId) => {
        setLoadingDir(itemId)
        try {
          const nodes = await fetchListing(itemId)
          return nodes.map((n) => ({ id: n.path, data: n }))
        } finally {
          setLoadingDir(null)
        }
      },
    },
    onPrimaryAction: (item) => {
      const node = item.getItemData()
      if (!node || node.isDir) return // dirs toggle via row click; read-only
      navigate(`/files?path=${encodeURIComponent(node.path)}`)
    },
    // No reordering/rename/dnd — read-only explorer (SPEC-16 §3).
    canReorder: false,
    features: [asyncDataLoaderFeature, hotkeysCoreFeature, searchFeature, selectionFeature],
    initialState: { expandedItems: [''] },
    // Client-side filter, no RPC (SPEC-16 §3). Search matches node names.
    isSearchMatchingItem: (search, item) => {
      const name = item.getItemData()?.name ?? item.getId()
      return name.toLowerCase().includes(search.toLowerCase())
    },
  })

  // Route arrival (e.g. from search): highlight the file and expand all parent
  // dirs in the live tree. loadChildrenIds resolves when that level's listing
  // has been fetched (async loader), then expand() the next ancestor.
  useEffect(() => {
    setActivePath(routePath)
    if (!routePath) return
    const parts = routePath.split('/').filter(Boolean)
    const dirs: string[] = []
    let dir = ''
    for (const p of parts.slice(0, -1)) {
      dir = dir ? `${dir}/${p}` : p
      dirs.push(dir)
    }
    let cancelled = false
    ;(async () => {
      // Ensure root listing loads first, then cascade top-down.
      let parent = ''
      for (const d of dirs) {
        if (cancelled) return
        try {
          await tree.loadChildrenIds(parent)
        } catch {
          return
        }
        const item = tree.getItemInstance(d)
        if (item.isFolder() && !item.isExpanded()) item.expand()
        parent = d
      }
    })()
    return () => {
      cancelled = true
    }
  }, [routePath, tree, setActivePath])

  // Mirror real expansion state into the store (project-switch reset in
  // setActiveProject collapses the live tree the next time a repo is selected).
  useEffect(() => {
    const open = tree.getState().expandedItems
    for (const id of open) setExpanded(id, true)
  }, [tree, setExpanded])

  // Search is applied imperatively when the filter string changes (avoiding a
  // render-phase side effect).
  useEffect(() => {
    tree.setSearch(filter || null)
  }, [tree, filter])

  // PLAN-08 T8.4: a file changed on disk → drop that file's parent dir from the
  // cache and re-fetch it so the tree reflects the change (e.g. new/renamed
  // file appears, git letter updates). Other dirs keep their cached listings.
  useEffect(() => {
    if (fileChangeEpoch === 0 || !lastChangedPath) return
    const parent = lastChangedPath.includes('/')
      ? lastChangedPath.slice(0, lastChangedPath.lastIndexOf('/'))
      : ''
    cacheRef.current.delete(parent)
    if (tree.getState().expandedItems.includes(parent) || parent === '') {
      void tree.loadChildrenIds(parent).then(() => tree.rebuildTree())
    }
  }, [fileChangeEpoch, lastChangedPath, tree])

  // headless-tree flattens visible (expanded) nodes into a flat meta list;
  // react-virtual renders only the viewport slice → 50k-file dirs stay
  // interactive (NFR-6, SPEC-16 §3).
  const items = tree.getItemsMeta()

  const virtualizer = useVirtualizer({
    count: items.length,
    getScrollElement: () => scrollRef.current,
    estimateSize: () => 26,
    overscan: 20,
  })

  return (
    <aside className="w-64 border-r border-border bg-surface shrink-0 flex flex-col min-h-0">
      <div className="px-3 py-2 flex items-center gap-2 shrink-0">
        <Search className="w-3.5 h-3.5 text-text-muted shrink-0" />
        <input
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          placeholder="Filter files…"
          className="w-full bg-transparent text-xs text-text-primary placeholder:text-text-muted outline-none"
          aria-label="Filter repo files"
        />
      </div>
      <div className="px-3 pb-2 flex items-center gap-2 border-b border-border-subtle shrink-0">
        <Folder className="w-3.5 h-3.5 text-accent shrink-0" />
        <span className="font-mono text-[11px] uppercase tracking-wide text-text-muted truncate">
          {projectName}
        </span>
      </div>
      <div
        ref={scrollRef}
        className="flex-1 overflow-y-auto min-h-0"
        role="tree"
        aria-label="Repository explorer"
      >
        <div style={{ height: virtualizer.getTotalSize(), position: 'relative' }}>
          {virtualizer.getVirtualItems().map((vi) => {
            const meta = items[vi.index]
            const item = tree.getItemInstance(meta.itemId)
            const node = item.getItemData()
            const isActive = meta.itemId === routePath
            const glyph = !node?.isDir ? GIT_GLYPH[node?.status ?? ''] : undefined
            return (
              <div
                key={item.getId()}
                {...item.getProps()}
                style={{
                  position: 'absolute',
                  top: 0,
                  left: 0,
                  width: '100%',
                  height: vi.size,
                  transform: `translateY(${vi.start}px)`,
                  paddingLeft: `${meta.level * 14 + 10}px`,
                }}
                className={`flex items-center gap-1.5 cursor-pointer select-none text-xs ${
                  isActive
                    ? 'bg-accent/15 text-accent font-medium'
                    : 'text-text-secondary hover:bg-surface-raised hover:text-text-primary'
                }`}
              >
                {node?.isDir ? (
                  <>
                    <ChevronRight
                      className={`w-3 h-3 shrink-0 transition-transform ${
                        item.isExpanded() ? 'rotate-90' : ''
                      }`}
                    />
                    {item.isExpanded() ? (
                      <FolderOpen className="w-3.5 h-3.5 shrink-0 text-text-muted" />
                    ) : (
                      <Folder className="w-3.5 h-3.5 shrink-0 text-text-muted" />
                    )}
                  </>
                ) : (
                  <>
                    <span className="w-3 shrink-0" />
                    <FileCode className="w-3.5 h-3.5 shrink-0 text-text-muted" />
                  </>
                )}
                <span className="truncate">{node?.name ?? item.getId()}</span>
                {glyph && (
                  <span
                    className={`ml-auto mr-1 shrink-0 font-mono text-[10px] ${glyph.cls}`}
                    title={glyph.label}
                  >
                    {glyph.label}
                  </span>
                )}
              </div>
            )
          })}
        </div>
      </div>
      <div className="px-3 py-1.5 border-t border-border-subtle flex items-center gap-2 shrink-0 text-[10px] text-text-muted">
        {routePath ? (
          <span className="font-mono truncate">…/{routePath.split('/').slice(-2).join('/')}</span>
        ) : (
          <span>{items.length} visible · lazy</span>
        )}
      </div>
    </aside>
  )
}