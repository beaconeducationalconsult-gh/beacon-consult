import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { doc, getDoc, serverTimestamp, updateDoc } from 'firebase/firestore'
import { db } from '../firebase'
import { useAuth } from '../context/AuthContext'
import { useToast } from '../context/ToastContext'
import { useCurriculum } from '../hooks/useCurriculum'
import SubjectSelect from '../components/SubjectSelect'
import { GRADES, TERMS, gradeLabel } from '../lib/grades'
import { buildLessonSlidesPptx, downloadLessonSlidesPptx } from '../lib/lessonSlidesPptx'
import SaveToLibrary from '../components/SaveToLibrary'
import { suggestFilename } from '../lib/generatedDocs'

const emptySlide = () => ({
  title: '',
  indicator: '',
  objectives: [],
  steps: [],
  assessment: '',
  keywords: [],
})

/** One line per entry, the way a teacher writes them. */
const toLines = (value) => (Array.isArray(value) ? value.join('\n') : value || '')
const fromLines = (value) => String(value || '')
  .split('\n')
  .map((line) => line.trim())
  .filter(Boolean)

/**
 * Edit a saved deck (P2-5).
 *
 * A deck is generated from the week's scheduled lessons, then edited — so this
 * form is about what the generator cannot know: which activities to keep, how to
 * phrase the objective, the closing question. Slides can be added, removed and
 * reordered; each field is written back as the array the exporter reads.
 */
export default function SlideLessonForm() {
  const { deckId } = useParams()
  const { profile } = useAuth()
  const toast = useToast()
  const navigate = useNavigate()

  const [deck, setDeck] = useState(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [busy, setBusy] = useState(false)
  const [notFound, setNotFound] = useState(false)
  const { subjects, loading: loadingSubjects, error: subjectsError } = useCurriculum(deck?.grade || 'B1')

  useEffect(() => {
    let active = true
    getDoc(doc(db, 'lesson_slides', deckId))
      .then((snap) => {
        if (!active) return
        if (snap.exists()) setDeck({ id: snap.id, ...snap.data() })
        else setNotFound(true)
      })
      .finally(() => active && setLoading(false))
    return () => {
      active = false
    }
  }, [deckId])

  const patchSlide = (index, changes) =>
    setDeck((current) => ({
      ...current,
      slides: current.slides.map((slide, i) => (i === index ? { ...slide, ...changes } : slide)),
    }))

  const move = (index, delta) =>
    setDeck((current) => {
      const slides = [...current.slides]
      const target = index + delta
      if (target < 0 || target >= slides.length) return current
      ;[slides[index], slides[target]] = [slides[target], slides[index]]
      return { ...current, slides }
    })

  const save = async (event) => {
    event.preventDefault()
    setSaving(true)
    try {
      const slides = (deck.slides || [])
        .map((slide) => ({ ...slide, title: slide.title?.trim() || 'Lesson' }))
        .filter((slide) => slide.title)
      await updateDoc(doc(db, 'lesson_slides', deckId), {
        title: deck.title || '',
        subjectId: deck.subjectId,
        subjectName: subjects.find((s) => s.id === deck.subjectId)?.name || deck.subjectName || deck.subjectId,
        grade: deck.grade,
        term: Number(deck.term) || 1,
        week: Number(deck.week) || 1,
        slides,
        updatedAt: serverTimestamp(),
      })
      toast.success('Deck updated')
      navigate(`/portal/slides/${deckId}`)
    } catch (error) {
      toast.error(`Could not save: ${error?.code || error.message}`)
    } finally {
      setSaving(false)
    }
  }

  const exportPptx = async () => {
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

  if (loading) return <div className="card h-96 animate-pulse" />
  if (notFound || !deck) {
    return (
      <div className="card p-6">
        <h1 className="page-title">Deck not found</h1>
        <p className="page-subtitle mt-2">It may have been deleted.</p>
        <Link to="/portal/slides" className="btn-secondary mt-4">Back to slide lessons</Link>
      </div>
    )
  }

  return (
    <form onSubmit={save}>
      <Link to={`/portal/slides/${deck.id}`} className="mb-6 inline-block text-sm text-slate-500 hover:text-slate-800">← Back to the deck</Link>

      <header className="mb-6">
        <h1 className="page-title">Edit deck</h1>
        <p className="page-subtitle">Slides are generated from the schedule — adjust the words your learners will read.</p>
      </header>

      <div className="card mb-4 space-y-4 p-5">
        <div className="grid gap-4 sm:grid-cols-4">
          <div>
            <label className="label-caps" htmlFor="d-grade">Grade</label>
            <select
              id="d-grade"
              className="input"
              value={deck.grade || 'B1'}
              onChange={(e) => setDeck((c) => ({ ...c, grade: e.target.value, subjectId: '' }))}
            >
              {GRADES.map((g) => <option key={g} value={g}>{gradeLabel(g)}</option>)}
            </select>
          </div>
          <div>
            <label className="label-caps" htmlFor="d-subject">Subject</label>
            <SubjectSelect
              id="d-subject"
              className="input"
              grade={deck.grade || 'B1'}
              subjects={subjects}
              loading={loadingSubjects}
              error={subjectsError}
              value={deck.subjectId || ''}
              onChange={(e) => setDeck((c) => ({ ...c, subjectId: e.target.value }))}
            />
          </div>
          <div>
            <label className="label-caps" htmlFor="d-term">Term</label>
            <select id="d-term" className="input" value={deck.term || 1} onChange={(e) => setDeck((c) => ({ ...c, term: e.target.value }))}>
              {TERMS.map((t) => <option key={t} value={t}>Term {t}</option>)}
            </select>
          </div>
          <div>
            <label className="label-caps" htmlFor="d-week">Week</label>
            <input
              id="d-week"
              type="number"
              min="1"
              max="14"
              className="input"
              value={deck.week || 1}
              onChange={(e) => setDeck((c) => ({ ...c, week: e.target.value }))}
            />
          </div>
        </div>
      </div>

      {(deck.slides || []).map((slide, index) => (
        <section key={index} className="card mb-4 space-y-3 p-5">
          <div className="flex items-center justify-between">
            <p className="label-caps">Slide {index + 1}</p>
            <div className="flex gap-2">
              <button type="button" className="btn-ghost px-2 py-1 text-xs" onClick={() => move(index, -1)} disabled={index === 0}>↑</button>
              <button type="button" className="btn-ghost px-2 py-1 text-xs" onClick={() => move(index, 1)} disabled={index === (deck.slides?.length || 0) - 1}>↓</button>
              <button
                type="button"
                className="btn-ghost px-2 py-1 text-xs text-red-600"
                onClick={() => setDeck((c) => ({ ...c, slides: c.slides.filter((_, i) => i !== index) }))}
              >
                Remove
              </button>
            </div>
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <label className="label-caps" htmlFor={`slide-title-${index}`}>Title</label>
              <input
                id={`slide-title-${index}`}
                className="input"
                value={slide.title || ''}
                onChange={(e) => patchSlide(index, { title: e.target.value })}
              />
            </div>
            <div>
              <label className="label-caps" htmlFor={`slide-indicator-${index}`}>Indicator code</label>
              <input
                id={`slide-indicator-${index}`}
                className="input font-mono"
                value={slide.indicator || ''}
                onChange={(e) => patchSlide(index, { indicator: e.target.value })}
              />
            </div>
          </div>

          <div className="grid gap-4 sm:grid-cols-3">
            <div>
              <label className="label-caps" htmlFor={`slide-objectives-${index}`}>Objectives (one per line)</label>
              <textarea
                id={`slide-objectives-${index}`}
                rows={3}
                className="input"
                value={toLines(slide.objectives)}
                onChange={(e) => patchSlide(index, { objectives: fromLines(e.target.value) })}
              />
            </div>
            <div>
              <label className="label-caps" htmlFor={`slide-steps-${index}`}>Activities (one per line)</label>
              <textarea
                id={`slide-steps-${index}`}
                rows={3}
                className="input"
                value={toLines(slide.steps)}
                onChange={(e) => patchSlide(index, { steps: fromLines(e.target.value) })}
              />
            </div>
            <div>
              <label className="label-caps" htmlFor={`slide-keywords-${index}`}>Key words (one per line)</label>
              <textarea
                id={`slide-keywords-${index}`}
                rows={3}
                className="input"
                value={toLines(slide.keywords)}
                onChange={(e) => patchSlide(index, { keywords: fromLines(e.target.value) })}
              />
            </div>
          </div>

          <div>
            <label className="label-caps" htmlFor={`slide-assessment-${index}`}>Closing question</label>
            <input
              id={`slide-assessment-${index}`}
              className="input"
              value={slide.assessment || ''}
              onChange={(e) => patchSlide(index, { assessment: e.target.value })}
            />
          </div>
        </section>
      ))}

      <div className="mb-6 flex flex-wrap gap-2">
        <button type="button" className="btn-secondary" onClick={() => setDeck((c) => ({ ...c, slides: [...(c.slides || []), emptySlide()] }))}>
          Add a slide
        </button>
        <button type="button" className="btn-secondary" onClick={exportPptx} disabled={busy}>
          {busy ? 'Building…' : 'Export .pptx'}
        </button>
        <SaveToLibrary
          kind="slide_deck"
          filename={suggestFilename('slide_deck', { subjectId: deck.subjectId, subjectName: deck.subjectName, grade: deck.grade, term: deck.term, week: deck.week }, 'pptx')}
          meta={{ subjectId: deck.subjectId, subjectName: deck.subjectName, grade: deck.grade, term: deck.term, week: deck.week, slides: deck.slides?.length }}
          build={() => buildLessonSlidesPptx(deck, { school: profile?.school }).write({ outputType: 'blob' })}
        />
      </div>

      <div className="flex justify-end gap-3">
        <Link to={`/portal/slides/${deck.id}`} className="btn-secondary">Cancel</Link>
        <button type="submit" className="btn-primary" disabled={saving}>
          {saving ? 'Saving…' : 'Save changes'}
        </button>
      </div>
    </form>
  )
}
