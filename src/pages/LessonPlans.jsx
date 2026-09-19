import { useState } from 'react'
import { Link } from 'react-router-dom'
import { deleteDoc, doc } from 'firebase/firestore'
import { db } from '../firebase'
import { useAuth } from '../context/AuthContext'
import { useToast } from '../context/ToastContext'
import { usePagedCollection } from '../hooks/useCollection'
import LoadMore from '../components/LoadMore'
import { SkeletonList } from '../components/Skeleton'
import DataError from '../components/DataError'
import EmptyState from '../components/EmptyState'
import ConfirmModal from '../components/ConfirmModal'
import NotesTabs from '../components/NotesTabs'
import SubjectIcon from '../components/SubjectIcon'
import { gradeLabel } from '../lib/grades'

/*
 * Shared = readable by the network. A plan saved with `visibility: 'private'`
 * is author-only, which is why this list cannot be one unfiltered query — see
 * the read rule for /lesson_plans/ and src/firestoreRules.test.js.
 */
const SHARED = [['visibility', 'in', ['members', 'public']]]

export default function LessonPlans() {
  const { user, isAdmin } = useAuth()
  const toast = useToast()
  const [scope, setScope] = useState('mine')
  const {
    rows, loading, error, hasMore, loadingMore, loadMore, moreError,
  } = usePagedCollection('lesson_plans', {
    filters: scope === 'mine' ? [['authorId', '==', user.uid]] : SHARED,
  })
  const [pendingDelete, setPendingDelete] = useState(null)

  const remove = async () => {
    try {
      await deleteDoc(doc(db, 'lesson_plans', pendingDelete.id))
      toast.success('Lesson plan deleted')
    } catch (error) {
      toast.error(`Could not delete: ${error?.code || error.message}`)
    } finally {
      setPendingDelete(null)
    }
  }

  return (
    <div>
      <header className="mb-6 flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="page-title">Lesson plans</h1>
          <p className="page-subtitle">Indicator-linked plans you can export to Word or PDF.</p>
        </div>
        <div className="flex gap-2">
          <Link to="/portal/curriculum" className="btn-secondary">Start from curriculum</Link>
          <Link to="/portal/plans/new" className="btn-primary">New plan</Link>
        </div>
      </header>

      <NotesTabs
        tabs={[
          { value: 'mine', label: 'Mine' },
          { value: 'shared', label: 'Shared' },
        ]}
        active={scope}
        onChange={setScope}
      />

      {error && <DataError what="lesson plans" error={error} />}
{loading && <SkeletonList rows={3} />}
      {!loading && !error && rows.length === 0 && (
        <EmptyState
          title={scope === 'mine' ? 'No plans yet' : 'Nothing shared here yet'}
          message="Open the curriculum browser and choose an indicator to build a plan around it."
          action={<Link to="/portal/plans/new" className="btn-primary mt-2">Create a lesson plan</Link>}
        />
      )}

      <ul className="grid gap-4 sm:grid-cols-2">
        {rows.map((plan) => (
          <li key={plan.id} className="card card-hover p-5">
            <div className="flex items-start gap-3">
              <SubjectIcon subjectId={plan.subjectId} name={plan.subjectName} />
              <div className="min-w-0 flex-1">
                <Link to={`/portal/plans/${plan.id}`} className="card-title block truncate hover:underline">
                  {(plan.indicatorCodes || [])[0] || plan.title || 'Lesson plan'}
                </Link>
                <p className="card-meta truncate">
                  {plan.subjectName || plan.subjectId} · {gradeLabel(plan.grade)} · Term {plan.term}, week {plan.week}
                </p>
                {plan.indicatorDescription && <p className="mt-2 line-clamp-2 text-sm text-slate-600">{plan.indicatorDescription}</p>}
                <p className="card-meta mt-2">{plan.authorName}</p>
                {(plan.authorId === user.uid || isAdmin) && (
                  <div className="mt-3 flex gap-2">
                    <Link to={`/portal/plans/${plan.id}/edit`} className="btn-secondary px-3 py-1.5 text-xs">Edit</Link>
                    <button type="button" className="btn-ghost px-3 py-1.5 text-xs" onClick={() => setPendingDelete(plan)}>Delete</button>
                  </div>
                )}
              </div>
            </div>
          </li>
        ))}
      </ul>

      <LoadMore hasMore={hasMore} loading={loadingMore} error={moreError} onLoad={loadMore} loaded={rows.length} />

      <ConfirmModal
        open={Boolean(pendingDelete)}
        title="Delete this lesson plan?"
        confirmLabel="Delete"
        onConfirm={remove}
        onCancel={() => setPendingDelete(null)}
      />
    </div>
  )
}
