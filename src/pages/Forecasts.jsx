import { useState } from 'react'
import { Link } from 'react-router-dom'
import { deleteDoc, doc } from 'firebase/firestore'
import { db } from '../firebase'
import { useAuth } from '../context/AuthContext'
import { useToast } from '../context/ToastContext'
import { useCollection } from '../hooks/useCollection'
import { SkeletonList } from '../components/Skeleton'
import EmptyState from '../components/EmptyState'
import ConfirmModal from '../components/ConfirmModal'
import NotesTabs from '../components/NotesTabs'
import SubjectIcon from '../components/SubjectIcon'
import { gradeLabel } from '../lib/grades'

export default function Forecasts() {
  const { user, isAdmin } = useAuth()
  const toast = useToast()
  const [scope, setScope] = useState('all')
  const { rows, loading } = useCollection('weekly_forecasts', { max: 60 })
  const [pendingDelete, setPendingDelete] = useState(null)

  const mine = rows.filter((r) => r.authorId === user.uid)
  const visible = scope === 'mine' ? mine : rows

  const remove = async () => {
    try {
      await deleteDoc(doc(db, 'weekly_forecasts', pendingDelete.id))
      toast.success('Scheme deleted')
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
          <h1 className="page-title">Schemes of learning</h1>
          <p className="page-subtitle">Term schemes built from the curriculum schedule, exportable to Word and PDF.</p>
        </div>
        <Link to="/portal/forecasts/new" className="btn-primary">New scheme</Link>
      </header>

      <NotesTabs
        tabs={[
          { value: 'all', label: 'All', count: rows.length },
          { value: 'mine', label: 'Mine', count: mine.length },
        ]}
        active={scope}
        onChange={setScope}
      />

      {loading && <SkeletonList rows={3} />}
      {!loading && visible.length === 0 && (
        <EmptyState
          title="No schemes yet"
          message="A scheme takes about five minutes: pick a subject, grade and term, and edit the weekly rows."
          action={<Link to="/portal/forecasts/new" className="btn-primary mt-2">Create a scheme</Link>}
        />
      )}

      <ul className="grid gap-4 sm:grid-cols-2">
        {visible.map((scheme) => (
          <li key={scheme.id} className="card card-hover p-5">
            <div className="flex items-start gap-3">
              <SubjectIcon subjectId={scheme.subjectId} name={scheme.subjectName} />
              <div className="min-w-0 flex-1">
                <Link to={`/portal/forecasts/${scheme.id}`} className="card-title block truncate hover:underline">
                  {scheme.subjectName || scheme.subjectId}
                </Link>
                <p className="card-meta">{gradeLabel(scheme.grade)} · Term {scheme.term} · {scheme.rows?.length || 0} weeks</p>
                <p className="card-meta mt-1">{scheme.authorName}</p>
                {(scheme.authorId === user.uid || isAdmin) && (
                  <div className="mt-3 flex gap-2">
                    <Link to={`/portal/forecasts/${scheme.id}/edit`} className="btn-secondary px-3 py-1.5 text-xs">Edit</Link>
                    <button type="button" className="btn-ghost px-3 py-1.5 text-xs" onClick={() => setPendingDelete(scheme)}>Delete</button>
                  </div>
                )}
              </div>
            </div>
          </li>
        ))}
      </ul>

      <ConfirmModal
        open={Boolean(pendingDelete)}
        title="Delete this scheme?"
        message="Exported files you already downloaded are unaffected."
        confirmLabel="Delete"
        onConfirm={remove}
        onCancel={() => setPendingDelete(null)}
      />
    </div>
  )
}
