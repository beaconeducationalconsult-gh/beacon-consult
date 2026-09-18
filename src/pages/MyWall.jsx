import { Link } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { useCollection } from '../hooks/useCollection'
import { SkeletonList } from '../components/Skeleton'
import EmptyState from '../components/EmptyState'
import { fmtDate } from '../lib/academicCalendar'

const SECTIONS = [
  { collection: 'lesson_plans', label: 'Lesson plans', to: (id) => `/portal/plans/${id}`, all: '/portal/plans' },
  { collection: 'weekly_forecasts', label: 'Schemes', to: (id) => `/portal/forecasts/${id}`, all: '/portal/forecasts' },
  { collection: 'notes', label: 'Study notes', to: (id) => `/portal/notes/${id}`, all: '/portal/notes' },
  { collection: 'questions', label: 'Questions', to: () => '/portal/questions', all: '/portal/questions' },
  { collection: 'articles', label: 'Articles', to: (id) => `/portal/articles/${id}`, all: '/portal/articles' },
]

function Section({ collection, label, to, all, uid }) {
  const { rows, loading, error } = useCollection(collection, { filters: [['authorId', '==', uid]], max: 20 })
  return (
    <section className="card p-5">
      <div className="flex items-center justify-between">
        <h2 className="card-title">{label}</h2>
        <span className="chip">{rows.length}</span>
      </div>
      {loading && <SkeletonList rows={1} />}
      {!loading && error && (
        <p className="card-meta mt-2 text-rose-700">Could not load your {label.toLowerCase()} ({error.code || 'error'}).</p>
      )}
      {!loading && !error && rows.length === 0 && <p className="card-meta mt-2">Nothing here yet.</p>}
      <ul className="mt-3 space-y-2">
        {rows.slice(0, 5).map((row) => (
          <li key={row.id} className="text-sm">
            <Link to={to(row.id)} className="text-slate-700 hover:text-brand-700 hover:underline">
              {row.title || row.prompt || row.subjectName || (row.indicatorCodes || [])[0] || 'Untitled'}
            </Link>
            <span className="card-meta ml-2">{fmtDate(row.createdAt)}</span>
          </li>
        ))}
      </ul>
      {rows.length > 5 && (
        <Link to={all} className="link mt-3 inline-block text-xs">
          See all {rows.length} →
        </Link>
      )}
    </section>
  )
}

export default function MyWall() {
  const { user, profile } = useAuth()

  return (
    <div>
      <header className="mb-6">
        <h1 className="page-title">My wall</h1>
        <p className="page-subtitle">Everything you have contributed to the network, in one place.</p>
      </header>

      {profile?.status === 'pending' && (
        <p className="card mb-4 border-l-4 border-l-amber-500 p-4 text-sm text-amber-800">
          Your account is still awaiting approval, so contributions may be limited until an administrator approves you.
        </p>
      )}

      <div className="grid gap-4 sm:grid-cols-2">
        {SECTIONS.map((section) => (
          <Section key={section.collection} {...section} uid={user.uid} />
        ))}
      </div>

      <div className="mt-6">
        <EmptyState
          title="Want to share something with the whole network?"
          message="Post an update on the feed — short thoughts, links you found useful, questions for other teachers."
          action={<Link to="/portal" className="btn-primary mt-2">Go to the feed</Link>}
        />
      </div>
    </div>
  )
}
