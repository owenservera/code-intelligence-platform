import { NavLink } from 'react-router-dom'
import {
  LayoutDashboard,
  Server,
  Database,
  Search,
  FileCode,
  ShieldCheck,
  BrainCircuit,
  BarChart3,
  Settings,
  PackageOpen,
  Sparkles,
  FolderKanban,
} from 'lucide-react'

const NAV_ITEMS = [
  { to: '/', icon: LayoutDashboard, label: 'Command Center' },
  { to: '/projects', icon: FolderKanban, label: 'Projects' },
  { to: '/daemon', icon: Server, label: 'Daemon & Servers' },
  { to: '/index', icon: Database, label: 'Index Management' },
  { to: '/search', icon: Search, label: 'Search & Navigate' },
  { to: '/files', icon: FileCode, label: 'File Intelligence' },
  { to: '/quality', icon: ShieldCheck, label: 'Quality & Audit' },
  { to: '/memory', icon: BrainCircuit, label: 'Memory Lab' },
  { to: '/visualize', icon: BarChart3, label: 'Visualizations' },
  { to: '/settings', icon: Settings, label: 'Settings' },
  { to: '/export', icon: PackageOpen, label: 'Export & Integrations' },
  { to: '/oracle', icon: Sparkles, label: 'Oracle / AI' },
]

export function LeftNav() {
  return (
    <nav className="w-52 border-r border-border bg-surface shrink-0 flex flex-col py-2 overflow-y-auto">
      {NAV_ITEMS.map(({ to, icon: Icon, label }) => (
        <NavLink
          key={to}
          to={to}
          end={to === '/'}
          className={({ isActive }) =>
            `flex items-center gap-2.5 px-3 py-2 mx-2 rounded-md text-xs transition-colors ${
              isActive
                ? 'bg-accent/15 text-accent font-medium'
                : 'text-text-secondary hover:bg-surface-raised hover:text-text-primary'
            }`
          }
        >
          <Icon className="w-4 h-4 shrink-0" />
          <span>{label}</span>
        </NavLink>
      ))}
    </nav>
  )
}
