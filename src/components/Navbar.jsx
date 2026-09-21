import { Link } from 'react-router-dom'
import ThemeToggle from './ThemeToggle'

/**
 * Public marketing navigation.
 * NOTE: the previous build shipped this unused (docs/gotchas.md). It is wired
 * into the public pages here — keep it that way or delete it.
 */
export default function Navbar() {
  return (
    <header className="border-b border-line bg-bg">
      <nav className="mx-auto flex max-w-6xl items-center justify-between px-4 py-4" aria-label="Main">
        <Link to="/" className="font-display text-xl font-bold text-brand-700 dark:text-brand-300">
          Beacon<span className="text-accent-500">.</span>
        </Link>
        <div className="flex items-center gap-1 sm:gap-4">
          <Link to="/vacancies" className="hidden rounded-lg px-3 py-2 text-sm font-medium text-muted hover:text-heading sm:block">
            Vacancies
          </Link>
          <Link to="/quotes" className="hidden rounded-lg px-3 py-2 text-sm font-medium text-muted hover:text-heading sm:block">
            Quotes
          </Link>
          <Link to="/calendar" className="hidden rounded-lg px-3 py-2 text-sm font-medium text-muted hover:text-heading sm:block">
            Calendar
          </Link>
          <Link to="/articles" className="rounded-lg px-3 py-2 text-sm font-medium text-muted hover:text-heading">
            Articles
          </Link>
          <ThemeToggle />
          <Link to="/login" className="btn-secondary">
            Sign in
          </Link>
          <Link to="/signup" className="btn-primary hidden sm:inline-flex">
            Join
          </Link>
        </div>
      </nav>
    </header>
  )
}
