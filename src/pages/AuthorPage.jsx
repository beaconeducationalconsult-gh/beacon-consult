import { Link, useParams } from 'react-router-dom'
import { useDoc, useCollection } from '../hooks/useCollection'
import { SkeletonList } from '../components/Skeleton'
import EmptyState from '../components/EmptyState'
import { fmtDate } from '../lib/academicCalendar'

/** Public-facing profile of a member, visible to signed-in members. */
export default function AuthorPage() {
  const { authorId } = useParams()
  const { row: profile, loading } = useDoc('users', authorId)
  const { rows: posts } = useCollection('posts', { filters: [['authorId', '==', authorId]], max: 20 })
  const { rows: plans } = useCollection('lesson_plans', { filters: [['authorId', '==', authorId]], max: 20 })

  if (loading) return <SkeletonList rows={3} />
  if (!profile) {
    return <EmptyState title="Member not found" message="This profile may have been removed." />
  }

  return (
    <div>
      <header className="card mb-6 flex flex-wrap items-center gap-4 p-6">
        <span className="grid h-16 w-16 place-items-center rounded-full bg-brand-600 text-xl font-bold text-white">
          {(profile.name || '?').slice(0, 1).toUpperCase()}
        </span>
        <div className="min-w-0 flex-1">
          <h1 className="page-title">{profile.name}</h1>
          <p className="page-subtitle">{profile.school || 'Beacon network'}</p>
          <p className="card-meta mt-1">
            {(profile.grades || []).join(' · ')}
            {profile.role === 'admin' && ' · administrator'}
          </p>
        </div>
        <dl className="flex gap-6 text-center">
          <div>
            <dt className="card-meta">Posts</dt>
            <dd className="text-lg font-bold text-slate-800">{posts.length}</dd>
          </div>
          <div>
            <dt className="card-meta">Plans</dt>
            <dd className="text-lg font-bold text-slate-800">{plans.length}</dd>
          </div>
        </dl>
      </header>

      <div className="grid gap-6 lg:grid-cols-2">
        <section>
          <h2 className="section-heading mb-3">Recent posts</h2>
          {posts.length === 0 ? (
            <p className="card p-5 text-sm text-slate-500">No posts yet.</p>
          ) : (
            <ul className="space-y-3">
              {posts.map((post) => (
                <li key={post.id} className="card p-4">
                  <p className="text-sm text-slate-700">{post.content}</p>
                  <p className="card-meta mt-2">
                    {fmtDate(post.timestamp)} · {post.likesCount || 0} likes
                  </p>
                </li>
              ))}
            </ul>
          )}
        </section>

        <section>
          <h2 className="section-heading mb-3">Lesson plans shared</h2>
          {plans.length === 0 ? (
            <p className="card p-5 text-sm text-slate-500">No lesson plans shared yet.</p>
          ) : (
            <ul className="space-y-3">
              {plans.map((plan) => (
                <li key={plan.id} className="card p-4">
                  <Link to={`/portal/plans/${plan.id}`} className="text-sm font-medium text-slate-800 hover:underline">
                    {(plan.indicatorCodes || [])[0] || plan.subjectName}
                  </Link>
                  <p className="card-meta mt-1">{plan.subjectName} · {plan.grade} · week {plan.week}</p>
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>
    </div>
  )
}
