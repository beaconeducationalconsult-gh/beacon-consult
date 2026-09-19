import { useState } from 'react'
import { NavLink, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

/** Inline 24×24 icon — the app uses no icon library (docs/conventions.md). */
const Icon = ({ path, className = 'h-4 w-4' }) => (
  <svg viewBox="0 0 24 24" className={className} fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
    {path}
  </svg>
)

const ICONS = {
  feed: <Icon path={<><path d="M4 5h16M4 12h16M4 19h10" /></>} />,
  curriculum: <Icon path={<><path d="M4 5.5A2.5 2.5 0 0 1 6.5 3H19v18H6.5A2.5 2.5 0 0 1 4 18.5v-13Z" /><path d="M9 3v18" /></>} />,
  wisdom: <Icon path={<><path d="M12 3l2.6 5.6 6.1.8-4.4 4.3 1 6-5.3-2.9-5.3 2.9 1-6L3.3 9.4l6.1-.8L12 3Z" /></>} />,
  articles: <Icon path={<><path d="M5 4h11l3 3v13H5z" /><path d="M8 10h8M8 14h8M8 18h5" /></>} />,
  forecasts: <Icon path={<><rect x="3" y="5" width="18" height="16" rx="2" /><path d="M3 10h18M8 3v4M16 3v4" /></>} />,
  plans: <Icon path={<><rect x="4" y="3" width="16" height="18" rx="2" /><path d="M8 8h8M8 12h8M8 16h5" /></>} />,
  questions: <Icon path={<><circle cx="12" cy="12" r="9" /><path d="M9.5 9.5a2.5 2.5 0 1 1 3.4 2.3c-.7.3-.9.9-.9 1.7M12 17h.01" /></>} />,
  notes: <Icon path={<><path d="M5 3h9l5 5v13H5z" /><path d="M14 3v5h5" /></>} />,
  vacancies: <Icon path={<><rect x="3" y="7" width="18" height="13" rx="2" /><path d="M8 7V5a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2M3 12h18" /></>} />,
  slides: <Icon path={<><rect x="3" y="4" width="18" height="12" rx="2" /><path d="M12 16v4M8 20h8" /></>} />,
  wall: <Icon path={<><rect x="3" y="3" width="7" height="7" rx="1" /><rect x="14" y="3" width="7" height="7" rx="1" /><rect x="3" y="14" width="7" height="7" rx="1" /><rect x="14" y="14" width="7" height="7" rx="1" /></>} />,
  search: <Icon path={<><circle cx="11" cy="11" r="7" /><path d="m20 20-3.5-3.5" /></>} />,
  progress: <Icon path={<><path d="M4 20V10M10 20V4M16 20v-7M22 20H2" /></>} />,
  calendar: <Icon path={<><rect x="3" y="5" width="18" height="16" rx="2" /><path d="M3 10h18M8 3v4M16 3v4" /></>} />,
  members: <Icon path={<><circle cx="9" cy="8" r="3.5" /><path d="M2.5 20a6.5 6.5 0 0 1 13 0M17 11.5a3 3 0 1 0 0-6M18 20h3.5a5.5 5.5 0 0 0-3-4.9" /></>} />,
  profile: <Icon path={<><circle cx="12" cy="8" r="4" /><path d="M4 21a8 8 0 0 1 16 0" /></>} />,
}

const LINKS = [
  // The old Feed page is now the Workspace: it also carries My wall and the
  // Calendar, which both moved into src/pages/Workspace.jsx.
  { to: '/portal', label: 'Workspace', icon: 'feed', end: true },
  { to: '/portal/curriculum', label: 'Curriculum', icon: 'curriculum' },
  { to: '/portal/forecasts', label: 'Schemes', icon: 'forecasts' },
  { to: '/portal/plans', label: 'Lesson plans', icon: 'plans' },
  { to: '/portal/questions', label: 'Question bank', icon: 'questions' },
  { to: '/portal/articles', label: 'Articles', icon: 'articles' },
  { to: '/portal/vacancies', label: 'Vacancies', icon: 'vacancies' },
  { to: '/portal/search', label: 'Search', icon: 'search' },
  { to: '/portal/library', label: 'My library', icon: 'wall' },
  { to: '/portal/progress', label: 'Progress', icon: 'progress' },

  // ── Hidden from the side panel, not removed ──────────────────────────────
  // These pages and routes still work and are still linked from elsewhere; only
  // the panel entries are commented out. Uncomment a line to show it again.
  // { to: '/portal/notes', label: 'Study notes', icon: 'notes' },
  // { to: '/portal/wisdom', label: 'Quote of the day', icon: 'wisdom' },
  // { to: '/portal/slides', label: 'Slide lessons', icon: 'slides' },
  // My wall is part of the Workspace now, so it has no entry of its own:
  // { to: '/portal/wall', label: 'My wall', icon: 'wall' },
]

export default function Sidebar() {
  const { profile, isAdmin, logout } = useAuth()
  const [open, setOpen] = useState(false)
  const navigate = useNavigate()

  const links = isAdmin ? [...LINKS, { to: '/portal/members', label: 'Members', icon: 'members', admin: true }] : LINKS

  const linkClass = ({ isActive }) =>
    `flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
      isActive ? 'bg-brand-50 text-brand-700' : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900'
    }`

  const nav = (
    <nav className="flex flex-1 flex-col gap-1 overflow-y-auto px-3 py-4" aria-label="Portal">
      {links.map((link) => (
        <NavLink key={link.to} to={link.to} end={link.end} className={linkClass} onClick={() => setOpen(false)}>
          {ICONS[link.icon]}
          <span className="flex-1">{link.label}</span>
          {link.admin && <span className="chip bg-amber-50 text-amber-700">admin</span>}
        </NavLink>
      ))}
    </nav>
  )

  const footer = (
    <div className="border-t border-slate-200 p-3">
      <NavLink to="/portal/profile" className="flex items-center gap-3 rounded-lg px-2 py-2 hover:bg-slate-100" onClick={() => setOpen(false)}>
        <span className="grid h-9 w-9 place-items-center rounded-full bg-brand-600 text-sm font-bold text-white">
          {(profile?.name || '?').slice(0, 1).toUpperCase()}
        </span>
        <span className="min-w-0 flex-1">
          <span className="block truncate text-sm font-semibold text-slate-800">{profile?.name || 'Member'}</span>
          <span className="block truncate text-xs text-slate-500">{profile?.school || 'Beacon Consult'}</span>
        </span>
      </NavLink>
      <button
        type="button"
        className="btn-ghost mt-1 w-full justify-start text-sm"
        onClick={() => {
          logout()
          navigate('/')
        }}
      >
        Sign out
      </button>
    </div>
  )

  return (
    <>
      {/* Mobile top bar */}
      <header className="sticky top-0 z-30 flex items-center justify-between border-b border-slate-200 bg-cream/95 px-4 py-3 backdrop-blur lg:hidden">
        <button
          type="button"
          className="btn-ghost px-2"
          aria-label="Open navigation"
          aria-expanded={open}
          onClick={() => setOpen(true)}
        >
          <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M4 6h16M4 12h16M4 18h16" strokeLinecap="round" />
          </svg>
        </button>
        <span className="font-display text-lg font-bold text-brand-700">Beacon</span>
        <span className="w-9" />
      </header>

      {open && (
        <div className="fixed inset-0 z-40 bg-slate-900/40 lg:hidden" onClick={() => setOpen(false)} aria-hidden="true" />
      )}

      {/* Desktop rail + mobile drawer */}
      <aside
        className={`fixed inset-y-0 left-0 z-50 flex w-56 flex-col border-r border-slate-200 bg-cream transition-transform lg:translate-x-0 ${
          open ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        <div className="flex items-center justify-between border-b border-slate-200 px-4 py-4">
          <NavLink to="/portal" className="font-display text-lg font-bold text-brand-700" onClick={() => setOpen(false)}>
            Beacon
          </NavLink>
          <button type="button" className="btn-ghost px-2 lg:hidden" aria-label="Close navigation" onClick={() => setOpen(false)}>
            ✕
          </button>
        </div>
        {nav}
        {footer}
      </aside>
    </>
  )
}
