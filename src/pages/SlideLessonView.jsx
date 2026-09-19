import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
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
import ConfirmModal from '../components/ConfirmModal'
import { gradeLabel } from '../lib/grades'
import { fmtDate } from '../lib/academicCalendar'
import { downloadLessonSlidesPptx } from '../lib/lessonSlidesPptx'

/**
 * One saved deck: the slides as a teacher would read them, a PPTX download, the
 * author's edit/delete controls, and the comment thread the rules already allow
 * on `lesson_slides/{id}/comments`.
 *
 * The deck view exists because the save button promised it ("share feedback with
 * comments from the deck page") and there was no page — P2-5.
 */
export default function SlideLessonView() {
  const { deckId } = useParams()
  const { row: deck, loading, error } = useDoc('lesson_slides', deckId)
  const { user, profile, isAdmin } = useAuth()
  const toast = useToast()
  const navigate = useNavigate()
  const [comments, setComments] = useState(null)
  const [text, setText] = useState('')
  const [posting, setPosting] = useState(false)
  const [busy, setBusy] = useState(false)
  const [pendingDelete, setPendingDelete] = useState(false)

  useEffect(() => {
    if (!deckId) return undefined
    return onSnapshot(
      query(collection(db, 'lesson_slides', deckId, 'comments'), orderBy('createdAt', 'asc')),
      (snap) => setComments(snap.docs.map((d) => ({ id: d.id, ...d.data() }))),
      (err) => {
        console.warn('[beacon] deck comments unavailable:', err?.code || err)
        setComments([])
      }
    )
  }, [deckId])

  const addComment = async (event) => {
    event.preventDefault()
    if (!text.trim()) return
    setPosting(true)
    try {
      await addDoc(collection(db, 'lesson_slides', deckId, 'comments'), {
        text: text.trim(),
        authorId: user.uid,
        authorName: profile?.name || 'Member',
        createdAt: serverTimestamp(),
      })
      await updateDoc(doc(db, 'lesson_slides', deckId), { commentCount: increment(1) })
      setText('')
    } catch (err) {
      toast.error(`Could not post the comment: ${err?.code || err.message}`)
    } finally {
      setPosting(false)
    }
  }

  const removeComment = async (commentId) => {
    try {
      await deleteDoc(doc(db, 'lesson_slides', deckId, 'comments', commentId))
      await updateDoc(doc(db, 'lesson_slides', deckId), { commentCount: increment(-1) })
    } catch (err) {
      toast.error(`Could not delete: ${err?.code || err.message}`)
    }
  }

  const exportPptx = async () => {
    setBusy(true)
    try {
      await downloadLessonSlidesPptx(deck, { school: profile?.school })
      toast.success('Slides downloaded')
    } catch (err) {
      toast.error(`Could not build the slides: ${err.message}`)
    } finally {
      setBusy(false)
    }
  }

  const remove = async () => {
    try {
      await deleteDoc(doc(db, 'lesson_slides', deckId))
      toast.success('Deck deleted')
      navigate('/portal/slides')
    } catch (err) {
      toast.error(`Could not delete: ${err?.code || err.message}`)
    } finally {
      setPendingDelete(false)
    }
  }

  if (loading) return <SkeletonList rows={2} />
  if (error) return <DataError what="this deck" error={error} />
  if (!deck) {
    return (
      <EmptyState
        title="Deck not found"
        message="It may have been deleted."
        action={<Link to="/portal/slides" className="btn-secondary mt-2">Back to slide lessons</Link>}
      />
    )
  }

  const canEdit = deck.authorId === user.uid || isAdmin

  return (
    <div>
      <Link to="/portal/slides" className="mb-6 inline-block text-sm text-slate-500 hover:text-slate-800">← Slide lessons</Link>

      <header className="mb-6">
        <h1 className="page-title text-3xl">{deck.subjectName || deck.subjectId} — {gradeLabel(deck.grade)}</h1>
        <p className="page-subtitle">
          Term {deck.term}, week {deck.week} · {deck.slides?.length || 0} slides · {deck.authorName} · {fmtDate(deck.createdAt)}
        </p>
        <div className="mt-3 flex flex-wrap gap-2">
          <button type="button" className="btn-accent" onClick={exportPptx} disabled={busy}>
            {busy ? 'Building…' : 'Export .pptx'}
          </button>
          {canEdit && <Link to={`/portal/slides/${deck.id}/edit`} className="btn-secondary">Edit deck</Link>}
          {canEdit && (
            <button type="button" className="btn-ghost" onClick={() => setPendingDelete(true)}>Delete</button>
          )}
        </div>
      </header>

      <ol className="space-y-4">
        {(deck.slides || []).map((slide, index) => (
          <li key={`${slide.title}-${index}`} className="card p-5">
            <p className="label-caps">Slide {index + 1}</p>
            <h2 className="card-title mt-1 text-lg">{slide.title}</h2>
            {slide.indicator && <p className="card-meta font-mono">{slide.indicator}</p>}
            {slide.objectives?.length > 0 && (
              <div className="mt-3">
                <p className="label-caps">Objectives</p>
                <ul className="mt-1 list-disc pl-5 text-sm text-slate-700">
                  {slide.objectives.map((line, i) => <li key={i}>{line}</li>)}
                </ul>
              </div>
            )}
            {slide.steps?.length > 0 && (
              <div className="mt-3">
                <p className="label-caps">Activities</p>
                <ol className="mt-1 list-decimal pl-5 text-sm text-slate-700">
                  {slide.steps.map((line, i) => <li key={i}>{line}</li>)}
                </ol>
              </div>
            )}
            {slide.assessment && (
              <p className="mt-3 text-sm italic text-amber-700">Check: {slide.assessment}</p>
            )}
            {slide.keywords?.length > 0 && (
              <p className="card-meta mt-3">{slide.keywords.join(' · ')}</p>
            )}
          </li>
        ))}
      </ol>
      {!deck.slides?.length && (
        <EmptyState title="This deck has no slides" message="Edit it to add some, or rebuild it from the schedule." />
      )}

      <section className="mt-8">
        <h2 className="section-heading">Comments ({deck.commentCount || 0})</h2>
        <form onSubmit={addComment} className="mt-3">
          <label className="sr-only" htmlFor="deck-comment">Add a comment</label>
          <textarea
            id="deck-comment"
            rows={2}
            className="input"
            placeholder="Did this deck work in your class? What would you change?"
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
        {comments?.length === 0 && <p className="mt-4 text-sm text-slate-500">No comments yet.</p>}
        <ul className="mt-4 space-y-3">
          {comments?.map((comment) => (
            <li key={comment.id} className="card p-4">
              <p className="card-meta">
                <span className="font-semibold text-slate-700">{comment.authorName}</span> · {fmtDate(comment.createdAt)}
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

      <ConfirmModal
        open={pendingDelete}
        title="Delete this deck?"
        confirmLabel="Delete"
        onConfirm={remove}
        onCancel={() => setPendingDelete(false)}
      />
    </div>
  )
}
