import { useState } from 'react'
import { Link } from 'react-router-dom'
import { deleteDoc, doc, serverTimestamp, updateDoc } from 'firebase/firestore'
import { db } from '../firebase'
import { useAuth } from '../context/AuthContext'
import { useToast } from '../context/ToastContext'
import { useCollection } from '../hooks/useCollection'
import { SkeletonList } from '../components/Skeleton'
import EmptyState from '../components/EmptyState'
import ConfirmModal from '../components/ConfirmModal'
import NotesTabs from '../components/NotesTabs'
import { fmtDate, daysUntil } from '../lib/academicCalendar'

export default function Vacancies() {
  const { user, isAdmin } = useAuth()
  const toast = useToast()
  const [scope, setScope] = useState('all')
  const { rows, loading } = useCollection('vacancies', { max: 60 })
  const [pendingDelete, setPendingDelete] = useState(null)

  const mine = rows.filter((v) => v.authorId === user.uid)
  const visible = scope === 'mine' ? mine : scope === 'published' ? rows.filter((v) => v.status === 'published') : rows

  const setStatus = async (vacancy, status) => {
    try {
      await updateDoc(doc(db, 'vacancies', vacancy.id), { status, updatedAt: serverTimestamp() })
      toast.success(status === 'published' ? 'Vacancy published' : status === 'closed' ? 'Vacancy closed' : 'Vacancy archived')
    } catch (error) {
      toast.error(`Could not update: ${error?.code || error.message}`)
    }
  }

  const remove = async () => {
    try {
      await deleteDoc(doc(db, 'vacancies', pendingDelete.id))
      toast.success('Vacancy deleted')
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
          <h1 className="page-title">Vacancies</h1>
          <p className="page-subtitle">Teaching openings. Published vacancies appear on the public website.</p>
        </div>
        <div className="flex gap-2">
          <Link to="/vacancies" className="btn-secondary">View public page ↗</Link>
          <Link to="/portal/vacancies/new" className="btn-primary">New vacancy</Link>
        </div>
      </header>

      <NotesTabs
        tabs={[
          { value: 'all', label: 'All', count: rows.length },
          { value: 'published', label: 'Published', count: rows.filter((v) => v.status === 'published').length },
          { value: 'mine', label: 'Mine', count: mine.length },
        ]}
        active={scope}
        onChange={setScope}
      />

      {loading && <SkeletonList rows={3} />}
      {!loading && visible.length === 0 && (
        <EmptyState
          title="No vacancies here"
          message="Post an opening and it becomes visible to teachers across the network — and on the public site once published."
          action={<Link to="/portal/vacancies/new" className="btn-primary mt-2">Post a vacancy</Link>}
        />
      )}

      <ul className="space-y-3">
        {visible.map((vacancy) => {
          const closing = vacancy.deadline ? daysUntil(vacancy.deadline) : null
          const canManage = vacancy.authorId === user.uid || isAdmin
          return (
            <li key={vacancy.id} className="card p-5">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div className="min-w-0">
                  <h2 className="card-title">{vacancy.role}</h2>
                  <p className="card-meta">{vacancy.school}</p>
                </div>
                <div className="flex items-center gap-2">
                  <span className={`chip ${vacancy.status === 'published' ? 'bg-emerald-50 text-emerald-700' : 'bg-slate-100 text-slate-600'}`}>
                    {vacancy.status}
                  </span>
                  {closing != null && <span className="chip">{closing < 0 ? 'closed' : `${closing}d left`}</span>}
                </div>
              </div>
              {vacancy.description && <p className="mt-3 text-sm text-slate-600">{vacancy.description}</p>}
              <p className="card-meta mt-2">
                {vacancy.subject} {vacancy.grade && `· ${vacancy.grade}`} {vacancy.deadline && `· closes ${fmtDate(vacancy.deadline)}`}
              </p>
              {canManage && (
                <div className="mt-3 flex flex-wrap gap-2">
                  <Link to={`/portal/vacancies/${vacancy.id}/edit`} className="btn-secondary px-3 py-1.5 text-xs">Edit</Link>
                  {vacancy.status !== 'published' ? (
                    <button type="button" className="btn-primary px-3 py-1.5 text-xs" onClick={() => setStatus(vacancy, 'published')}>Publish</button>
                  ) : (
                    <button type="button" className="btn-secondary px-3 py-1.5 text-xs" onClick={() => setStatus(vacancy, 'closed')}>Close</button>
                  )}
                  <button type="button" className="btn-ghost px-3 py-1.5 text-xs" onClick={() => setPendingDelete(vacancy)}>Delete</button>
                </div>
              )}
            </li>
          )
        })}
      </ul>

      <ConfirmModal open={Boolean(pendingDelete)} title="Delete this vacancy?" confirmLabel="Delete" onConfirm={remove} onCancel={() => setPendingDelete(null)} />
    </div>
  )
}
