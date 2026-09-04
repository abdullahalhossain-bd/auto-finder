import { useEffect, useState } from 'react'
import { NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'
import { api } from '../lib/api'
import {
  LayoutDashboard,
  Megaphone,
  Users,
  CheckSquare,
  Ban,
  LogOut,
  Settings,
  CreditCard,
  LayoutGrid,
  Menu,
  X,
  BarChart3,
  Plug,
  Send,
  Contact,
  Sparkles,
  Bot,
  Gift,
  ShieldCheck,
  FileBarChart,
} from 'lucide-react'

type NavItem = { to: string; label: string; icon: typeof LayoutDashboard; badge?: string }

const navPrimary: NavItem[] = [
  { to: '/', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/leads/generate', label: 'Generate Leads', icon: Sparkles, badge: 'AI' },
  { to: '/campaigns', label: 'Campaigns', icon: Megaphone },
  { to: '/leads', label: 'Leads', icon: Contact },
  { to: '/pipeline', label: 'Pipeline', icon: LayoutGrid },
]

const navOutreach: NavItem[] = [
  { to: '/approvals', label: 'Approvals', icon: CheckSquare },
  { to: '/outreach', label: 'Outreach', icon: Send },
  { to: '/outreach/auto-reply', label: 'Auto-Reply', icon: Bot },
  { to: '/inbox', label: 'Inbox', icon: Users },
  { to: '/suppression', label: 'Do Not Contact', icon: Ban },
]

const navAccount: NavItem[] = [
  { to: '/analytics', label: 'Analytics', icon: BarChart3 },
  { to: '/lead-quality', label: 'Lead Quality Report', icon: FileBarChart },
  { to: '/integrations', label: 'Integrations', icon: Plug },
  { to: '/referrals', label: 'Referrals', icon: Gift },
  { to: '/billing', label: 'Billing', icon: CreditCard },
  { to: '/settings', label: 'Settings', icon: Settings },
]

export default function Layout() {
  const { logout } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [mobileOpen, setMobileOpen] = useState(false)
  const [isPlatformAdmin, setIsPlatformAdmin] = useState(false)

  useEffect(() => {
    setMobileOpen(false)
  }, [location.pathname])

  useEffect(() => {
    api
      .adminMe()
      .then((me) => setIsPlatformAdmin(Boolean(me.is_platform_admin)))
      .catch(() => setIsPlatformAdmin(false))
  }, [])

  useEffect(() => {
    if (mobileOpen) {
      document.body.style.overflow = 'hidden'
    } else {
      document.body.style.overflow = ''
    }
    return () => {
      document.body.style.overflow = ''
    }
  }, [mobileOpen])

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  const sidebar = (
    <>
      <div className="p-5 border-b border-white/10">
        <h1 className="font-bold text-lg tracking-tight">LocalOpp Finder</h1>
        <p className="text-xs text-blue-200 mt-0.5">AI Sales Agent</p>
      </div>
      <nav className="flex-1 p-3 space-y-4 overflow-y-auto" aria-label="Main">
        {(
          [
            { title: null, items: navPrimary },
            { title: 'Outreach', items: navOutreach },
            { title: 'Account', items: navAccount },
            ...(isPlatformAdmin
              ? [
                  {
                    title: 'Platform',
                    items: [
                      { to: '/admin', label: 'Admin', icon: ShieldCheck },
                    ] as NavItem[],
                  },
                ]
              : []),
          ] as { title: string | null; items: NavItem[] }[]
        ).map((group, gi) => (
          <div key={gi} className="space-y-1">
            {group.title && (
              <p className="px-3 pt-1 pb-1 text-[10px] font-semibold uppercase tracking-wider text-blue-300/70">
                {group.title}
              </p>
            )}
            {group.items.map(({ to, label, icon: Icon, badge }) => (
              <NavLink
                key={to}
                to={to}
                end={to === '/'}
                className={({ isActive }) =>
                  `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition focus:outline-none focus-visible:ring-2 focus-visible:ring-white/60 ${
                    isActive
                      ? 'bg-white/15 text-white font-medium'
                      : 'text-blue-100 hover:bg-white/10'
                  }`
                }
              >
                <Icon size={18} aria-hidden />
                <span className="flex-1">{label}</span>
                {badge && (
                  <span className="text-[10px] font-semibold bg-brand-400/90 text-brand-950 px-1.5 py-0.5 rounded-full">
                    {badge}
                  </span>
                )}
              </NavLink>
            ))}
          </div>
        ))}
      </nav>
      <button
        type="button"
        onClick={handleLogout}
        className="m-3 flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm text-blue-100 hover:bg-white/10 focus:outline-none focus-visible:ring-2 focus-visible:ring-white/60"
      >
        <LogOut size={18} aria-hidden />
        Logout
      </button>
    </>
  )

  return (
    <div className="min-h-screen flex bg-slate-50">
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:absolute focus:z-[100] focus:top-2 focus:left-2 focus:bg-white focus:text-brand-700 focus:px-4 focus:py-2 focus:rounded-lg focus:shadow-lg focus:outline-none"
      >
        Skip to main content
      </a>
      <aside
        className="hidden md:flex w-56 bg-brand-900 text-white flex-col shrink-0"
        aria-label="Sidebar"
      >
        {sidebar}
      </aside>

      {mobileOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/40 md:hidden"
          aria-hidden
          onClick={() => setMobileOpen(false)}
        />
      )}

      <aside
        className={`fixed inset-y-0 left-0 z-50 w-64 max-w-[85vw] bg-brand-900 text-white flex flex-col transform transition-transform duration-200 ease-out md:hidden ${
          mobileOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
        aria-label="Mobile menu"
        aria-hidden={!mobileOpen}
      >
        <div className="flex items-center justify-between p-4 border-b border-white/10">
          <span className="font-bold">Menu</span>
          <button
            type="button"
            onClick={() => setMobileOpen(false)}
            className="p-2 rounded-lg hover:bg-white/10 focus:outline-none focus-visible:ring-2 focus-visible:ring-white/60"
            aria-label="Close menu"
          >
            <X size={20} />
          </button>
        </div>
        <div className="flex flex-col flex-1 overflow-hidden">{sidebar}</div>
      </aside>

      <div className="flex-1 flex flex-col min-w-0">
        <header className="md:hidden sticky top-0 z-30 flex items-center gap-3 px-4 py-3 bg-white border-b border-slate-200">
          <button
            type="button"
            onClick={() => setMobileOpen(true)}
            className="p-2 -ml-1 rounded-lg text-slate-700 hover:bg-slate-100 focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-500"
            aria-label="Open menu"
            aria-expanded={mobileOpen}
          >
            <Menu size={22} />
          </button>
          <span className="font-semibold text-slate-900 truncate">
            LocalOpp Finder
          </span>
        </header>

        <main id="main-content" className="flex-1 overflow-auto" tabIndex={-1}>
          <div className="max-w-6xl mx-auto p-4 sm:p-6">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  )
}
