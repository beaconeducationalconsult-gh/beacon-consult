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
import { fmtDate } from '../lib/academicCalendar'

export default function Notes() {
  const { user, isAdmin } = useAuth()
  const toast = useToast()
  const [scope, setScope] = useState('all')
  const { rows, loading } = useCollection('notes', { max: 80 })
  const [pendingDelete, setPendingDelete] = useState(null)

  const visible = scope === 'mine' ? rows.filter((n) => n.authorId === user.uid) : rows

  const remove = async () => {
    try {
      await deleteDoc(doc(db, 'notes', pendingDelete.id))
      toast.success('Note deleted')
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
          <h1 className="page-title">Study notes</h1>
          <p className="page-subtitle">Lesson notes and revision summaries, shared with the network.</p>
        </div>
        <Link to="/portal/notes/new" className="btn-primary">New note</Link>
      </header>

      <NotesTabs
        tabs={[
          { value: 'all', label: 'All', count: rows.length },
          { value: 'mine', label: 'Mine', count: rows.filter((n) => n.authorId === user.uid).length },
        ]}
        active={scope}
        onChange={setScope}
      />

      {loading && <SkeletonList rows={3} />}
      {!loading && visible.length === 0 && (
        <EmptyState
          title="No notes yet"
          message="Notes are shorter than articles — a summary of a sub-strand, a revision sheet, a worked example."
          action={<Link to="/portal/notes/new" className="btn-primary mt-2">Write a note</Link>}
        />
      )}

      <ul className="grid gap-4 sm:grid-cols-2">
        {visible.map((note) => (
          <li key={note.id} className="card card-hover p-5">
            <div className="flex items-start gap-3">
              <SubjectIcon subjectId={note.subjectId} name={note.subjectName} />
              <div className="min-w-0 flex-1">
                <Link to={`/portal/notes/${note.id}`} className="card-title block truncate hover:underline">{note.title}</Link>
                <p className="card-meta">
                  {note.subjectName || note.subjectId} {note.grade ? `· ${gradeLabel(note.grade)}` : ''}
                </p>
                <p className="card-meta mt-1">{note.authorName} · {fmtDate(note.createdAt)}</p>
                {note.summary && <p className="mt-2 line-clamp-2 text-sm text-slate-600">{note.summary}</p>}
                {(note.authorId === user.uid || isAdmin) && (
                  <div className="mt-3 flex gap-2">
                    <Link to={`/portal/notes/${note.id}/edit`} className="btn-secondary px-3 py-1.5 text-xs">Edit</Link>
                    <button type="button" className="btn-ghost px-3 py-1.5 text-xs" onClick={() => setPendingDelete(note)}>Delete</button>
                  </div>
                )}
              </div>
            </div>
          </li>
        ))}
      </ul>

      <ConfirmModal open={Boolean(pendingDelete)} title="Delete this note?" confirmLabel="Delete" onConfirm={remove} onCancel={() => setPendingDelete(null)} />
    </div>
  )
}
