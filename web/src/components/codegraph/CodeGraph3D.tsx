import { useEffect, useRef, useState } from 'react'
import * as THREE from 'three'
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js'
import { CSS2DRenderer, CSS2DObject } from 'three/examples/jsm/renderers/CSS2DRenderer.js'
import type { GraphPayload, GraphNode, GraphEdge } from '@/lib/api'
import { Loader2, AlertTriangle } from 'lucide-react'

// SPEC-09 E1: interactive 3D code graph. Nodes are spheres coloured by symbol
// kind; edges are lines coloured by link kind. OrbitControls give
// zoom/pan/rotate. Click a node → expand. Search query glows matching nodes.
// Heavy (three.js ~180KB) so it is lazy-loaded only when the Visualize tab opens.

const KIND_COLORS: Record<string, string> = {
  function: '#60a5fa',
  method: '#60a5fa',
  class: '#f472b6',
  interface: '#c084fc',
  module: '#34d399',
  import: '#94a3b8',
  variable: '#fbbf24',
  constant: '#fb923c',
  default: '#a3a3a3',
}

const LINK_COLORS: Record<string, string> = {
  reference: '#64748b',
  imports: '#3b82f6',
  co_change: '#f43f5e',
  calls: '#22d3ee',
  default: '#52525b',
}

export function kindColor(kind?: string): string {
  return KIND_COLORS[kind ?? ''] ?? KIND_COLORS.default
}

export function linkColor(kind?: string): string {
  return LINK_COLORS[kind ?? ''] ?? LINK_COLORS.default
}

export function CodeGraph3D({
  graph,
  query,
  onExpand,
  depth,
  direction,
  onDepthChange,
  onDirectionChange,
}: {
  graph: GraphPayload & { lod_fallback?: boolean }
  query: string
  onExpand: (id: string) => void
  depth: number
  direction: 'in' | 'out' | 'both'
  onDepthChange: (d: number) => void
  onDirectionChange: (d: 'in' | 'out' | 'both') => void
}) {
  const mountRef = useRef<HTMLDivElement>(null)
  const [hovered, setHovered] = useState<string | null>(null)

  useEffect(() => {
    const mount = mountRef.current
    if (!mount || !graph.nodes?.length) return

    const width = mount.clientWidth || 600
    const height = mount.clientHeight || 420

    const scene = new THREE.Scene()
    scene.background = new THREE.Color('#0b0d12')
    const camera = new THREE.PerspectiveCamera(55, width / height, 0.1, 1000)
    camera.position.set(16, 12, 20)

    const renderer = new THREE.WebGLRenderer({ antialias: true })
    renderer.setSize(width, height)
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
    mount.appendChild(renderer.domElement)

    const labelRenderer = new CSS2DRenderer()
    labelRenderer.setSize(width, height)
    labelRenderer.domElement.style.position = 'absolute'
    labelRenderer.domElement.style.top = '0'
    labelRenderer.domElement.style.pointerEvents = 'none'
    mount.appendChild(labelRenderer.domElement)

    const controls = new OrbitControls(camera, renderer.domElement)
    controls.enableDamping = true
    controls.dampingFactor = 0.08
    controls.minDistance = 4
    controls.maxDistance = 120

    scene.add(new THREE.AmbientLight(0xffffff, 0.55))
    const keyLight = new THREE.DirectionalLight(0xffffff, 0.9)
    keyLight.position.set(10, 20, 10)
    scene.add(keyLight)
    const fillLight = new THREE.DirectionalLight(0xffffff, 0.25)
    fillLight.position.set(-10, -5, -10)
    scene.add(fillLight)

    // Force layout: const iterations of repulsion + springs.
    const nodes: GraphNode[] = graph.nodes ?? []
    const idSet = new Map<string, number>()
    nodes.forEach((n, i) => idSet.set(n.id, i))
    const pos = nodes.map(() => new THREE.Vector3(
      (Math.random() - 0.5) * 10,
      (Math.random() - 0.5) * 10,
      (Math.random() - 0.5) * 10,
    ))
    const k = 1.4
    const edges: GraphEdge[] = graph.edges ?? []
    for (let iter = 0; iter < 120; iter++) {
      for (let i = 0; i < nodes.length; i++) {
        for (let j = i + 1; j < nodes.length; j++) {
          const d = pos[i].distanceTo(pos[j]) || 0.01
          const f = (k * k) / d
          const dir = pos[i].clone().sub(pos[j]).normalize()
          pos[i].addScaledVector(dir, f * 0.02)
          pos[j].addScaledVector(dir, -f * 0.02)
        }
      }
      for (const e of edges) {
        const a = idSet.get(e.src)
        const b = idSet.get(e.dst)
        if (a === undefined || b === undefined) continue
        const d = pos[a].distanceTo(pos[b]) || 0.01
        const tol = 1.8
        if (d > tol) {
          const dir = pos[a].clone().sub(pos[b]).normalize()
          const pull = (d - tol) * 0.02
          pos[a].addScaledVector(dir, -pull)
          pos[b].addScaledVector(dir, pull)
        }
      }
    }
    // Center the layout.
    const center = new THREE.Vector3()
    pos.forEach((p) => center.add(p))
    center.divideScalar(pos.length)
    pos.forEach((p) => p.sub(center))

    const nodeMeshes = new Map<string, THREE.Mesh>()
    const nodeLabels = new Map<string, CSS2DObject>()
    const nodeGeos: THREE.SphereGeometry[] = []

    const q = query.trim().toLowerCase()
    nodes.forEach((n, i) => {
      const geo = new THREE.SphereGeometry(n.kind === 'module' ? 0.55 : 0.38, 20, 20)
      nodeGeos.push(geo)
      const color = new THREE.Color(kindColor(n.kind))
      // Search-highlight: matching nodes glow warm.
      const hit = q && (n.name?.toLowerCase().includes(q) || n.path?.toLowerCase().includes(q))
      const mat = new THREE.MeshStandardMaterial({
        color: hit ? new THREE.Color('#fbbf24') : color,
        emissive: hit ? new THREE.Color('#b45309') : new THREE.Color('#000000'),
        emissiveIntensity: hit ? 0.8 : 0,
        metalness: 0.15,
        roughness: 0.5,
      })
      const mesh = new THREE.Mesh(geo, mat)
      mesh.position.copy(pos[i])
      mesh.userData.id = n.id

      const div = document.createElement('div')
      div.textContent = n.name ?? n.id.slice(0, 10)
      div.style.font = '10px ui-monospace, monospace'
      div.style.color = '#e4e4e7'
      div.style.background = 'rgba(9,11,16,0.82)'
      div.style.padding = '1px 5px'
      div.style.borderRadius = '999px'
      div.style.border = `1px solid ${color.getStyle()}`
      div.style.pointerEvents = 'none'
      div.style.whiteSpace = 'nowrap'
      const lbl = new CSS2DObject(div)
      lbl.position.copy(pos[i])
      lbl.position.y += 0.75

      scene.add(mesh)
      scene.add(lbl)
      nodeMeshes.set(n.id, mesh)
      nodeLabels.set(n.id, lbl)
    })

    // Edges as thin lines.
    const edgePts: number[] = []
    for (const e of edges) {
      const a = idSet.get(e.src)
      const b = idSet.get(e.dst)
      if (a === undefined || b === undefined) continue
      const from = pos[a]
      const to = pos[b]
      const step = 6
      for (let s = 0; s < step; s++) {
        const t = s / step
        edgePts.push(
          from.x + (to.x - from.x) * t,
          from.y + (to.y - from.y) * t,
          from.z + (to.z - from.z) * t,
        )
      }
    }
    const edgeGeo = new THREE.BufferGeometry()
    const nodesArr = new Float32Array(edgePts)
    edgeGeo.setAttribute('position', new THREE.BufferAttribute(nodesArr, 3))
    const edgeMat = new THREE.LineBasicMaterial({ color: '#334155', transparent: true, opacity: 0.6 })
    const edgeLine = new THREE.LineSegments(edgeGeo, edgeMat)
    scene.add(edgeLine)

    const raycaster = new THREE.Raycaster()
    const mouse = new THREE.Vector2()
    renderer.domElement.addEventListener('click', (ev) => {
      const rect = renderer.domElement.getBoundingClientRect()
      mouse.x = ((ev.clientX - rect.left) / rect.width) * 2 - 1
      mouse.y = -((ev.clientY - rect.top) / rect.height) * 2 + 1
      raycaster.setFromCamera(mouse, camera)
      const hits = raycaster.intersectObjects([...nodeMeshes.values()])
      if (hits.length) {
        const id = hits[0].object.userData.id as string
        onExpand(id)
      }
    })

    renderer.domElement.addEventListener('mousemove', (ev) => {
      const rect = renderer.domElement.getBoundingClientRect()
      const x = ((ev.clientX - rect.left) / rect.width) * 2 - 1
      const y = -((ev.clientY - rect.top) / rect.height) * 2 + 1
      mouse.set(x, y)
      raycaster.setFromCamera(mouse, camera)
      const hits = raycaster.intersectObjects([...nodeMeshes.values()])
      const id = hits.length ? (hits[0].object.userData.id as string) : null
      setHovered(id)
    })

    let raf = 0
    const animate = () => {
      raf = requestAnimationFrame(animate)
      controls.update()
      renderer.render(scene, camera)
      labelRenderer.render(scene, camera)
    }
    animate()

    const onResize = () => {
      const w = mount.clientWidth || 600
      const h = mount.clientHeight || 420
      camera.aspect = w / h
      camera.updateProjectionMatrix()
      renderer.setSize(w, h)
      labelRenderer.setSize(w, h)
    }
    window.addEventListener('resize', onResize)

    return () => {
      cancelAnimationFrame(raf)
      window.removeEventListener('resize', onResize)
      mount.removeChild(renderer.domElement)
      mount.removeChild(labelRenderer.domElement)
      renderer.dispose()
      controls.dispose()
      nodeGeos.forEach((g) => g.dispose())
      edgeGeo.dispose()
      edgeMat.dispose()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [graph, query])

  // 2D LOD fallback (E2): graph too large → SVG overlay, no WebGL.
  if (graph.lod_fallback) {
    return <LodFallback graph={graph} onExpand={onExpand} />
  }

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-2">
        <select
          value={direction}
          onChange={(e) => onDirectionChange(e.target.value as 'in' | 'out' | 'both')}
          className="rounded-lg border border-border bg-surface px-2 py-1 text-xs text-text-primary"
        >
          <option value="both">both directions</option>
          <option value="in">incoming</option>
          <option value="out">outgoing</option>
        </select>
        {[1, 2, 3].map((d) => (
          <button
            key={d}
            onClick={() => onDepthChange(d)}
            className={`px-2.5 py-1 rounded-full text-[11px] font-medium border transition-colors cursor-pointer ${
              depth === d
                ? 'bg-accent/20 text-accent border-accent/50'
                : 'border-border-subtle text-text-muted hover:border-border'
            }`}
          >
            depth {d}
          </button>
        ))}
        <span className="ml-auto text-[10px] text-text-muted font-mono">
          {graph.nodes?.length} nodes · {graph.edges?.length} edges
        </span>
      </div>
      <div ref={mountRef} className="relative h-[420px] rounded-lg border border-border bg-bg overflow-hidden">
        {hovered && <HoverChip graph={graph} id={hovered} />}
        {graph.nodes?.length === 0 && (
          <div className="absolute inset-0 flex items-center justify-center">
            <p className="text-xs text-text-muted">No graph to render — pick a symbol.</p>
          </div>
        )}
      </div>
      <div className="flex flex-wrap gap-3 text-[10px] text-text-muted">
        {Object.entries(KIND_COLORS).filter(([k]) => k !== 'default').map(([k, c]) => (
          <span key={k} className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full" style={{ background: c }} />
            {k}
          </span>
        ))}
        <span className="flex items-center gap-1.5">
          <span className="w-2 h-2 rounded-full" style={{ background: LINK_COLORS.reference }} /> reference
        </span>
        <span className="flex items-center gap-1.5">
          <span className="w-2 h-2 rounded-full" style={{ background: LINK_COLORS.imports }} /> imports
        </span>
        <span className="flex items-center gap-1.5">
          <span className="w-2 h-2 rounded-full" style={{ background: LINK_COLORS.co_change }} /> co-change
        </span>
        <span className="ml-auto text-[10px] text-text-muted">drag orbit · scroll zoom · click expand</span>
      </div>
    </div>
  )
}

function HoverChip({ graph, id }: { graph: GraphPayload; id: string }) {
  const n = graph.nodes?.find((x) => x.id === id)
  if (!n) return null
  return (
    <div className="absolute left-3 top-3 z-10 rounded-lg border border-border bg-surface px-3 py-2 text-[11px] shadow-lg">
      <p className="text-text-primary font-medium">{n.name ?? id}</p>
      <p className="text-text-muted font-mono">{n.kind} · {n.path}</p>
    </div>
  )
}

// E2: 2D LOD fallback — canvas-free SVG ring when caps are hit.
function LodFallback({ graph, onExpand }: { graph: GraphPayload; onExpand: (id: string) => void }) {
  const nodes = graph.nodes ?? []
  const edges = graph.edges ?? []
  const cx = 260
  const cy = 170
  const R = 120
  const angle = (i: number) => (i / Math.max(1, nodes.length)) * Math.PI * 2 - Math.PI / 2
  const pos = new Map<string, [number, number]>(
    nodes.map((n, i) => [n.id, [cx + R * Math.cos(angle(i)), cy + R * Math.sin(angle(i))]]),
  )
  return (
    <div className="rounded-lg border border-border bg-bg p-4">
      <div className="flex items-center gap-2 mb-3 text-[11px] text-warning">
        <AlertTriangle className="w-3.5 h-3.5" />
        Too large for full 3D — 2D LOD showing {nodes.length} nodes / {edges.length} edges.
        Click a node to expand.
      </div>
      <svg viewBox="0 0 520 340" className="w-full h-[340px]">
        {edges.map((e, i) => {
          const a = pos.get(e.src)
          const b = pos.get(e.dst)
          if (!a || !b) return null
          return (
            <line key={i} x1={a[0]} y1={a[1]} x2={b[0]} y2={b[1]}
              stroke={linkColor(e.kind)} strokeWidth="0.6" opacity="0.55" />
          )
        })}
        {nodes.map((n) => {
          const p = pos.get(n.id)
          if (!p) return null
          return (
            <g key={n.id} onClick={() => onExpand(n.id)} className="cursor-pointer">
              <circle cx={p[0]} cy={p[1]} r={n.kind === 'module' ? 8 : 5.5}
                fill={kindColor(n.kind)} opacity="0.9" />
              <text x={p[0]} y={p[1] + 16} textAnchor="middle"
                className="text-[9px] fill-text-muted font-mono">
                {(n.name ?? n.id).slice(0, 14)}
              </text>
            </g>
          )
        })}
      </svg>
    </div>
  )
}

export function GraphLoader() {
  return (
    <div className="h-[420px] flex items-center justify-center rounded-lg border border-border bg-bg">
      <Loader2 className="w-4 h-4 animate-spin text-accent" /> Loading 3D graph…
    </div>
  )
}