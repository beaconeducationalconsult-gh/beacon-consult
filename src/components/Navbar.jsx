import { useState } from 'react'
import { Link } from 'react-router-dom'
import ThemeToggle from './ThemeToggle'
import { cn } from '../ui/cn'

const LINKS = [
  { to: '/vacancies', label: 'Vacancies' },
  { to: '/quotes', label: 'Quotes' },
  { to: '/calendar', label: 'Calendar' },
  { to: '/articles', label: 'Articles' },
]

/**
 * Public marketing navigation, rendered once by PublicLayout.
 * Desktop shows the links inline; below `sm:` they collapse into a menu rather
 * than disappearing (the old behaviour).
 */
export default function Navbar() {
  const [open, setOpen] = useState(false)

  return (
    <header className="border-b border-line bg-bg">
      <nav className="mx-auto flex max-w-6xl items-center justify-between px-4 py-4" aria-label="Main">
        <Link to="/" className="font-display text-xl font-bold text-brand-700 dark:text-brand-300">
          Beacon<span className="text-accent-500">.</span>
        </Link>

        <div className="flex items-center gap-1 sm:gap-2">
          {LINKS.map((link) => (
            <Link
              key={link.to}
              to={link.to}
              className="hidden rounded-lg px-3 py-2 text-sm font-medium text-muted hover:text-heading sm:block"
            >
              {link.label}
            </Link>
          ))}
          <ThemeToggle />
          <Link to="/login" className="btn-secondary hidden sm:inline-flex">
            Sign in
          </Link>
          <Link to="/signup" className="btn-primary hidden sm:inline-flex">
            Join
          </Link>
          <button
            type="button"
            className="btn-ghost px-2 sm:hidden"
            aria-label={open ? 'Close menu' : 'Open menu'}
            aria-expanded={open}
            onClick={() => setOpen((o) => !o)}
          >
            <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
              <path d={open ? 'M6 6l12 12M18 6L6 18' : 'M4 6h16M4 12h16M4 18h16'} strokeLinecap="round" />
            </svg>
          </button>
        </div>
      </nav>

      <div className={cn('sm:hidden', open ? 'block' : 'hidden')}>
        <div className="space-y-1 border-t border-line px-4 py-3">
          {LINKS.map((link) => (
            <Link
              key={link.to}
              to={link.to}
              onClick={() => setOpen(false)}
              className="block rounded-lg px-3 py-2 text-sm font-medium text-muted hover:bg-surface-2 hover:text-heading"
            >
              {link.label}
            </Link>
          ))}
          <div className="flex gap-2 pt-2">
            <Link to="/login" onClick={() => setOpen(false)} className="btn-secondary flex-1">
              Sign in
            </Link>
            <Link to="/signup" onClick={() => setOpen(false)} className="btn-primary flex-1">
              Join
            </Link>
          </div>
        </div>
      </div>
    </header>
  )
}
