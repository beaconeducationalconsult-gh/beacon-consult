import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import Button from '../ui/Button'
import IconButton from '../ui/IconButton'
import Avatar from '../ui/Avatar'
import Menu, { MenuItem, MenuLabel, MenuDivider } from '../ui/Menu'
import ThemeToggle from './ThemeToggle'
import OfflineIndicator from './OfflineIndicator'

const NEW_ITEMS = [
  { to: '/portal/articles/new', label: 'Article' },
  { to: '/portal/forecasts/new', label: 'Scheme of learning' },
  { to: '/portal/plans/new', label: 'Lesson plan' },
  { to: '/portal/questions/new', label: 'Question' },
  { to: '/portal/notes/new', label: 'Study note' },
  { to: '/portal/vacancies/new', label: 'Vacancy' },
  { to: '/portal/slides', label: 'Slide lesson' },
]

/**
 * Persistent portal top bar: global search, "+ New" menu, connection status,
 * theme toggle and the account menu. The hamburger (mobile only) opens the
 * sidebar Drawer via `onMenu`.
 */
export default function TopBar({ onMenu }) {
  const { profile, logout } = useAuth()
  const navigate = useNavigate()
  const [term, setTerm] = useState('')

  const submitSearch = (e) => {
    e.preventDefault()
    const q = term.trim()
    navigate(q ? `/portal/search?q=${encodeURIComponent(q)}` : '/portal/search')
  }

  return (
    <header className="sticky top-0 z-30 flex items-center gap-2 border-b border-line bg-bg/95 px-4 py-2.5 backdrop-blur md:px-6">
      <IconButton label="Open navigation" className="lg:hidden" onClick={onMenu}>
        <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
          <path d="M4 6h16M4 12h16M4 18h16" strokeLinecap="round" />
        </svg>
      </IconButton>

      <form onSubmit={submitSearch} role="search" className="relative min-w-0 flex-1 md:max-w-md">
        <svg
          viewBox="0 0 24 24"
          className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-subtle"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          aria-hidden="true"
        >
          <circle cx="11" cy="11" r="7" />
          <path d="m20 20-3.5-3.5" strokeLinecap="round" />
        </svg>
        <input
          type="search"
          value={term}
          onChange={(e) => setTerm(e.target.value)}
          placeholder="Search everything…"
          aria-label="Search curriculum and shared resources"
          className="w-full rounded-lg border border-line-2 bg-surface py-2 pl-9 pr-3 text-sm text-heading placeholder:text-subtle focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
        />
      </form>

      <div className="ml-auto flex items-center gap-1">
        <OfflineIndicator className="mr-1 hidden sm:inline-flex" />

        <Menu
          trigger={({ toggle, ref, ariaProps }) => (
            <Button ref={ref} onClick={toggle} size="sm" {...ariaProps}>
              <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
                <path d="M12 5v14M5 12h14" strokeLinecap="round" />
              </svg>
              <span className="hidden sm:inline">New</span>
            </Button>
          )}
        >
          <MenuLabel>Create</MenuLabel>
          {NEW_ITEMS.map((item) => (
            <MenuItem key={item.to} to={item.to}>
              {item.label}
            </MenuItem>
          ))}
        </Menu>

        <ThemeToggle />

        <Menu
          trigger={({ toggle, ref, ariaProps }) => (
            <button
              ref={ref}
              type="button"
              onClick={toggle}
              className="rounded-full transition-opacity hover:opacity-90"
              aria-label="Account menu"
              {...ariaProps}
            >
              <Avatar name={profile?.name || 'Member'} size="sm" />
            </button>
          )}
        >
          <div className="px-3 py-2">
            <p className="truncate text-sm font-semibold text-heading">{profile?.name || 'Member'}</p>
            <p className="truncate text-xs text-muted">{profile?.school || 'Beacon Consult'}</p>
          </div>
          <MenuDivider />
          <MenuItem to="/portal/profile">Profile</MenuItem>
          <MenuItem
            onClick={() => {
              logout()
              navigate('/')
            }}
          >
            Sign out
          </MenuItem>
        </Menu>
      </div>
    </header>
  )
}
