import { useState } from 'react'
import { Link } from 'react-router-dom'
import { addDoc, collection, deleteDoc, doc, serverTimestamp } from 'firebase/firestore'
import { db } from '../firebase'
import { useAuth } from '../context/AuthContext'
import { useToast } from '../context/ToastContext'
import { useCollection } from '../hooks/useCollection'
import { useCurriculum, useSchedules } from '../hooks/useCurriculum'
import SubjectSelect from '../components/SubjectSelect'
import { GRADES, TERMS, gradeLabel } from '../lib/grades'
import { downloadLessonSlidesPptx } from '../lib/lessonSlidesPptx'
import { SkeletonList } from '../components/Skeleton'
import DataError from '../components/DataError'
import EmptyState from '../components/EmptyState'

/** Turn a week's scheduled lessons into a presentation deck. */
export default function SlideLessons() {
  const { user, profile } = useAuth()
  const toast = useToast()
  const [grade, setGrade] = useState('B1')
  const [subjectId, setSubjectId] = useState('')
  const [term, setTerm] = useState(1)
  const [week, setWeek] = useState(1)
  const [busy, setBusy] = useState(false)
  const { subjects, loading: loadingSubjects, error: subjectsError } = useCurriculum(grade)
  const { lessons } = useSchedules(grade, subjectId)
  const { rows: decks, loading, error } = useCollection('lesson_slides', { max: 40, ordered: true })

  const buildDeck = () => {
    const subjectName = subjects.find((s) => s.id === subjectId)?.name || subjectId
    const weekLessons = lessons.filter(
      (lesson) =>
        (lesson.subjectId === subjectId || lesson.subject === subjectId) &&
        Number(lesson.term) === Number(term) &&
        Number(lesson.week) === Number(week)
    )
    if (!weekLessons.length) {
      toast.error('No scheduled lessons for that subject, term and week.')
      return null
    }
    return {
      subjectId,
      subjectName,
      grade,
      term: Number(term),
      week: Number(week),
      slides: weekLessons.map((lesson) => ({
        title: lesson.sessionTitle || lesson.performanceIndicator || lesson.indicatorDescription || 'Lesson',
        indicator: lesson.indicatorCode || lesson.code,
        objectives: [lesson.performanceIndicator || lesson.indicatorDescription].filter(Boolean),
        keywords: [].concat(lesson.keywords || []).filter(Boolean),
        steps: [].concat(lesson.main || lesson.starter || []).slice(0, 6),
        assessment: lesson.assessment || '',
      })),
    }
  }

  const exportDeck = async () => {
    const deck = buildDeck()
    if (!deck) return
    setBusy(true)
    try {
      await downloadLessonSlidesPptx(deck, { school: profile?.school })
      toast.success('Slides downloaded')
    } catch (error) {
      toast.error(`Could not build the slides: ${error.message}`)
    } finally {
      setBusy(false)
    }
  }

  const saveDeck = async () => {
    const deck = buildDeck()
    if (!deck) return
    setBusy(true)
    try {
      await addDoc(collection(db, 'lesson_slides'), {
        ...deck,
        authorId: user.uid,
        authorName: profile?.name || 'Member',
        status: 'draft',
        commentCount: 0,
        createdAt: serverTimestamp(),
      })
      toast.success('Deck saved — share feedback with comments from the deck page.')
    } catch (error) {
      toast.error(`Could not save: ${error?.code || error.message}`)
    } finally {
      setBusy(false)
    }
  }

  const remove = async (id) => {
    try {
      await deleteDoc(doc(db, 'lesson_slides', id))
      toast.success('Deck removed')
    } catch (error) {
      toast.error(`Could not delete: ${error?.code || error.message}`)
    }
  }

  return (
    <div>
      <header className="mb-6">
        <h1 className="page-title">Slide lessons</h1>
        <p className="page-subtitle">
          Build a presentation from the week's scheduled lessons. Useful for revision and for sharing
          with colleagues who teach the same class.
        </p>
      </header>

      <div className="card space-y-5 p-6">
        <div className="grid gap-4 sm:grid-cols-4">
          <div>
            <label className="label-caps" htmlFor="s-grade">Grade</label>
            <select id="s-grade" className="input" value={grade} onChange={(e) => { setGrade(e.target.value); setSubjectId('') }}>
              {GRADES.map((g) => <option key={g} value={g}>{gradeLabel(g)}</option>)}
            </select>
          </div>
          <div>
            <label className="label-caps" htmlFor="s-subject">Subject</label>
            <SubjectSelect
              id="s-subject"
              className="input"
              grade={grade}
              subjects={subjects}
              loading={loadingSubjects}
              error={subjectsError}
              value={subjectId}
              onChange={(e) => setSubjectId(e.target.value)}
            />
          </div>
          <div>
            <label className="label-caps" htmlFor="s-term">Term</label>
            <select id="s-term" className="input" value={term} onChange={(e) => setTerm(e.target.value)}>
              {TERMS.map((t) => <option key={t} value={t}>Term {t}</option>)}
            </select>
          </div>
          <div>
            <label className="label-caps" htmlFor="s-week">Week</label>
            <input id="s-week" type="number" min="1" max="14" className="input" value={week} onChange={(e) => setWeek(e.target.value)} />
          </div>
        </div>

        <div className="flex flex-wrap justify-end gap-2">
          <button type="button" className="btn-secondary" onClick={saveDeck} disabled={busy || !subjectId}>Save deck</button>
          <button type="button" className="btn-accent" onClick={exportDeck} disabled={busy || !subjectId}>
            {busy ? 'Working…' : 'Export .pptx'}
          </button>
        </div>
      </div>

      <h2 className="section-heading mb-3 mt-8">Saved decks</h2>
      {error && <DataError what="slide decks" error={error} />}
{loading && <SkeletonList rows={2} />}
      {!loading && !error && decks.length === 0 && (
        <EmptyState title="No decks saved yet" message="Build one above and save it so colleagues can use it too." />
      )}
      <ul className="space-y-3">
        {decks.map((deck) => (
          <li key={deck.id} className="card flex flex-wrap items-center justify-between gap-3 p-5">
            <div>
              <Link to={`/portal/slides/${deck.id}`} className="card-title hover:underline">
                {deck.subjectName} · {gradeLabel(deck.grade)}
              </Link>
              <p className="card-meta">
                Term {deck.term}, week {deck.week} · {deck.slides?.length || 0} slides · {deck.authorName}
              </p>
            </div>
            <div className="flex gap-2">
              <button type="button" className="btn-secondary px-3 py-1.5 text-xs" onClick={() => downloadLessonSlidesPptx(deck, { school: profile?.school })}>
                Download
              </button>
              {deck.authorId === user.uid && (
                <button type="button" className="btn-ghost px-3 py-1.5 text-xs" onClick={() => remove(deck.id)}>Delete</button>
              )}
            </div>
          </li>
        ))}
      </ul>

      <p className="card-meta mt-6">
        Looking for quiz slides instead? <Link to="/portal/questions/quiz" className="link">Use the quiz maker</Link>.
      </p>
    </div>
  )
}
