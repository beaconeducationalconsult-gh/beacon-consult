import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import {
  addDoc, collection, deleteDoc, doc, increment, onSnapshot, orderBy, query, serverTimestamp, updateDoc,
} from 'firebase/firestore'
import { db } from '../firebase'
import { useDoc } from '../hooks/useCollection'
import { useAuth } from '../context/AuthContext'
import { useToast } from '../context/ToastContext'
import { SkeletonList } from '../components/Skeleton'
import DataError from '../components/DataError'
import EmptyState from '../components/EmptyState'
import { gradeLabel } from '../lib/grades'
import { fmtDate } from '../lib/academicCalendar'

/** A note plus its comment thread (subcollection `comments`). */
export default function NoteView() {
  const { noteId } = useParams()
  const { row: note, loading, error } = useDoc('notes', noteId)
  const { user, profile, isAdmin } = useAuth()
  const toast = useToast()
  const [comments, setComments] = useState(null)
  const [text, setText] = useState('')
  const [posting, setPosting] = useState(false)

  useEffect(() => {
    if (!noteId) return undefined
    return onSnapshot(
      query(collection(db, 'notes', noteId, 'comments'), orderBy('createdAt', 'asc')),
      (snap) => setComments(snap.docs.map((d) => ({ id: d.id, ...d.data() }))),
      (error) => {
        console.warn('[beacon] note comments unavailable:', error?.code || error)
        setComments([])
      }
    )
  }, [noteId])

  const addComment = async (event) => {
    event.preventDefault()
    if (!text.trim()) return
    setPosting(true)
    try {
      await addDoc(collection(db, 'notes', noteId, 'comments'), {
        text: text.trim(),
        authorId: user.uid,
        authorName: profile?.name || 'Member',
        createdAt: serverTimestamp(),
      })
      await updateDoc(doc(db, 'notes', noteId), { commentCount: increment(1) })
      setText('')
    } catch (error) {
      toast.error(`Could not post the comment: ${error?.code || error.message}`)
    } finally {
      setPosting(false)
    }
  }

  const removeComment = async (commentId) => {
    try {
      await deleteDoc(doc(db, 'notes', noteId, 'comments', commentId))
      await updateDoc(doc(db, 'notes', noteId), { commentCount: increment(-1) })
    } catch (error) {
      toast.error(`Could not delete: ${error?.code || error.message}`)
    }
  }

  if (loading) return <SkeletonList rows={2} />
  if (error) return <DataError what="this note" error={error} />
  if (!note) {
    return (
      <EmptyState
        title="Note not found"
        message="It may have been deleted."
        action={<Link to="/portal/notes" className="btn-secondary mt-2">Back to notes</Link>}
      />
    )
  }

  const canEdit = note.authorId === user.uid || isAdmin

  return (
    <div>
      <Link to="/portal/notes" className="mb-6 inline-block text-sm text-slate-500 hover:text-slate-800">← Study notes</Link>

      <header className="mb-6">
        <h1 className="page-title text-3xl">{note.title}</h1>
        <p className="page-subtitle">
          {note.subjectName || note.subjectId} · {gradeLabel(note.grade)} · {note.authorName} ·{' '}
          {fmtDate(note.createdAt)}
        </p>
        {canEdit && (
          <div className="mt-3 flex gap-2">
            <Link to={`/portal/notes/${note.id}/edit`} className="btn-secondary">Edit</Link>
          </div>
        )}
      </header>

      {note.summary && <p className="card mb-4 p-4 text-sm text-slate-600">{note.summary}</p>}

      <article className="card p-8">
        <div className="prose prose-slate max-w-none" dangerouslySetInnerHTML={{ __html: note.content || '' }} />
      </article>

      <section className="mt-8">
        <h2 className="section-heading">Comments ({note.commentCount || 0})</h2>

        <form onSubmit={addComment} className="mt-3">
          <label className="sr-only" htmlFor="comment">Add a comment</label>
          <textarea
            id="comment"
            rows={2}
            className="input"
            placeholder="Ask a question or add what worked for you…"
            value={text}
            onChange={(e) => setText(e.target.value)}
          />
          <div className="mt-2 flex justify-end">
            <button type="submit" className="btn-primary" disabled={posting || !text.trim()}>
              {posting ? 'Posting…' : 'Comment'}
            </button>
          </div>
        </form>

        {comments === null && <SkeletonList rows={2} />}
        {comments?.length === 0 && <p className="mt-4 text-sm text-slate-500">No comments yet — start the conversation.</p>}

        <ul className="mt-4 space-y-3">
          {comments?.map((comment) => (
            <li key={comment.id} className="card p-4">
              <p className="card-meta">
                <span className="font-semibold text-slate-700">{comment.authorName}</span> ·{' '}
                {fmtDate(comment.createdAt)}
              </p>
              <p className="mt-2 text-sm text-slate-700">{comment.text}</p>
              {(comment.authorId === user.uid || isAdmin) && (
                <button type="button" className="mt-2 text-xs font-semibold text-red-600 hover:underline" onClick={() => removeComment(comment.id)}>
                  Delete
                </button>
              )}
            </li>
          ))}
        </ul>
      </section>
    </div>
  )
}
