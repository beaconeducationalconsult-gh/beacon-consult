import { NavLink, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import Drawer from '../ui/Drawer'
import IconButton from '../ui/IconButton'
import Avatar from '../ui/Avatar'
import { cn } from '../ui/cn'

/** Inline 24×24 icon — the app uses no icon library (docs/conventions.md). */
const Icon = ({ path, className = 'h-5 w-5' }) => (
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
  progress: <Icon path={<><path d="M4 20V10M10 20V4M16 20v-7M22 20H2" /></>} />,
  members: <Icon path={<><circle cx="9" cy="8" r="3.5" /><path d="M2.5 20a6.5 6.5 0 0 1 13 0M17 11.5a3 3 0 1 0 0-6M18 20h3.5a5.5 5.5 0 0 0-3-4.9" /></>} />,
}

/*
 * Grouped portal navigation. The link targets are read as text by
 * sidebarRoutes.test.js, which asserts every one names a real route — keep each
 * link written as a literal `to` property holding a `/portal` path. Notes,
 * Wisdom and Slides were hidden from the old panel; the redesign restores them
 * to the IA (their routes always existed).
 */
const GROUPS = [
  {
    label: 'Teach',
    links: [
      { to: '/portal', label: 'Workspace', icon: 'feed', end: true },
      { to: '/portal/curriculum', label: 'Curriculum', icon: 'curriculum' },
      { to: '/portal/forecasts', label: 'Schemes', icon: 'forecasts' },
      { to: '/portal/plans', label: 'Lesson plans', icon: 'plans' },
      { to: '/portal/questions', label: 'Question bank', icon: 'questions' },
      { to: '/portal/questions/exam', label: 'Exam builder', icon: 'questions' },
      { to: '/portal/models', label: 'Teaching models', icon: 'slides' },
    ],
  },
  {
    label: 'Create',
    links: [
      { to: '/portal/articles', label: 'Articles', icon: 'articles' },
      { to: '/portal/vacancies', label: 'Vacancies', icon: 'vacancies' },
      { to: '/portal/slides', label: 'Slide lessons', icon: 'slides' },
    ],
  },
  {
    label: 'You',
    links: [
      { to: '/portal/library', label: 'My library', icon: 'wall' },
      { to: '/portal/progress', label: 'Progress', icon: 'progress' },
      { to: '/portal/notes', label: 'Study notes', icon: 'notes' },
      { to: '/portal/wisdom', label: 'Quote of the day', icon: 'wisdom' },
    ],
  },
]

const ADMIN_LINK = { to: '/portal/members', label: 'Members', icon: 'members', admin: true }

/**
 * The sidebar body (brand, grouped nav, user footer). Rendered twice: once in
 * the desktop rail (honouring `collapsed`) and once in the mobile Drawer
 * (always expanded). `onNavigate` closes the drawer after a click.
 */
function SidebarBody({ collapsed, isAdmin, profile, onNavigate, onLogout }) {
  const linkClass = ({ isActive }) =>
    cn(
      'flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors',
      collapsed && 'justify-center px-0',
      isActive
        ? 'bg-brand-50 text-brand-700 dark:bg-brand-500/15 dark:text-brand-300'
        : 'text-muted hover:bg-surface-2 hover:text-heading'
    )

  const renderLink = (link) => (
    <NavLink key={link.to} to={link.to} end={link.end} className={linkClass} title={link.label} onClick={onNavigate}>
      {ICONS[link.icon]}
      {!collapsed && <span className="flex-1 truncate">{link.label}</span>}
      {link.admin && !collapsed && <span className="chip bg-warning-50 text-warning-700">admin</span>}
    </NavLink>
  )

  const group = (g) => (
    <div key={g.label}>
      {collapsed ? (
        <div className="mx-auto mb-2 mt-2 h-px w-6 bg-line" aria-hidden="true" />
      ) : (
        <p className="mb-1 px-3 text-xs font-semibold uppercase tracking-wide text-subtle">{g.label}</p>
      )}
      <div className="space-y-1">{g.links.map(renderLink)}</div>
    </div>
  )

  return (
    <>
      <nav className="flex-1 space-y-4 overflow-y-auto px-3 py-4" aria-label="Portal">
        {GROUPS.map(group)}
        {isAdmin && group({ label: 'Admin', links: [ADMIN_LINK] })}
      </nav>

      <div className="border-t border-line p-3">
        <div className={cn('flex items-center gap-2', collapsed && 'flex-col')}>
          <NavLink
            to="/portal/profile"
            className={cn('flex min-w-0 flex-1 items-center gap-3 rounded-lg px-2 py-2 hover:bg-surface-2', collapsed && 'flex-none px-0')}
            title="Your profile"
            onClick={onNavigate}
          >
            <Avatar name={profile?.name || 'Member'} size="sm" />
            {!collapsed && (
              <span className="min-w-0 flex-1">
                <span className="block truncate text-sm font-semibold text-heading">{profile?.name || 'Member'}</span>
                <span className="block truncate text-xs text-muted">{profile?.school || 'Beacon Consult'}</span>
              </span>
            )}
          </NavLink>
          <IconButton
            label="Sign out"
            size="sm"
            onClick={() => {
              onLogout()
            }}
          >
            <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <path d="M15 17l5-5-5-5M20 12H9M12 19H5V5h7" />
            </svg>
          </IconButton>
        </div>
      </div>
    </>
  )
}

export default function Sidebar({ open, onClose, collapsed, onToggleCollapse }) {
  const { profile, isAdmin, logout } = useAuth()
  const navigate = useNavigate()

  const signOut = () => {
    logout()
    navigate('/')
  }

  return (
    <>
      {/* Desktop rail — collapses to an icon rail; its width drives the content margin in App. */}
      <aside
        className={cn(
          'fixed inset-y-0 left-0 z-40 hidden flex-col border-r border-line bg-bg transition-[width] duration-200 lg:flex',
          collapsed ? 'lg:w-16' : 'lg:w-64'
        )}
      >
        <div className={cn('flex items-center border-b border-line py-4', collapsed ? 'justify-center px-2' : 'justify-between gap-2 px-4')}>
          {!collapsed && (
            <NavLink to="/portal" className="flex items-center gap-2 font-display text-lg font-bold text-brand-700 dark:text-brand-300">
              <span className="grid h-8 w-8 shrink-0 place-items-center rounded-lg bg-brand-600 text-white">B</span>
              <span>Beacon</span>
            </NavLink>
          )}
          <IconButton label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'} size="sm" onClick={onToggleCollapse}>
            <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <path d={collapsed ? 'M9 6l6 6-6 6' : 'M15 6l-6 6 6 6'} />
            </svg>
          </IconButton>
        </div>
        <SidebarBody collapsed={collapsed} isAdmin={isAdmin} profile={profile} onLogout={signOut} />
      </aside>

      {/* Mobile drawer — focus-trapped; always expanded. */}
      <Drawer open={open} onClose={onClose} label="Portal navigation" className="w-64">
        <div className="flex items-center justify-between border-b border-line px-4 py-4">
          <NavLink to="/portal" className="flex items-center gap-2 font-display text-lg font-bold text-brand-700 dark:text-brand-300" onClick={onClose}>
            <span className="grid h-8 w-8 shrink-0 place-items-center rounded-lg bg-brand-600 text-white">B</span>
            <span>Beacon</span>
          </NavLink>
          <IconButton label="Close navigation" size="sm" onClick={onClose}>
            <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" aria-hidden="true">
              <path d="M6 6l12 12M18 6L6 18" />
            </svg>
          </IconButton>
        </div>
        <SidebarBody collapsed={false} isAdmin={isAdmin} profile={profile} onNavigate={onClose} onLogout={signOut} />
      </Drawer>
    </>
  )
}
