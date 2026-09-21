import { Link } from 'react-router-dom'
import { currentYear } from '../lib/academicCalendar'

/** Shared public footer, rendered once by PublicLayout. */
export default function Footer() {
  return (
    <footer className="border-t border-line bg-surface">
      <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-3 px-4 py-8 text-sm text-muted">
        <p>© {currentYear()} Beacon Educational Consult. Curriculum data from NaCCA.</p>
        <div className="flex gap-4">
          <Link to="/articles" className="hover:text-heading">Articles</Link>
          <Link to="/vacancies" className="hover:text-heading">Vacancies</Link>
          <Link to="/quotes" className="hover:text-heading">Quotes</Link>
          <Link to="/calendar" className="hover:text-heading">Calendar</Link>
        </div>
      </div>
    </footer>
  )
}
