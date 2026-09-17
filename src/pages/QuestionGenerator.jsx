import { useState } from 'react'
import { Link } from 'react-router-dom'
import { addDoc, collection, serverTimestamp } from 'firebase/firestore'
import { db } from '../firebase'
import { useAuth } from '../context/AuthContext'
import { useToast } from '../context/ToastContext'
import { useCurriculum, useSchedules } from '../hooks/useCurriculum'
import SubjectSelect from '../components/SubjectSelect'
import { GRADES, gradeLabel } from '../lib/grades'
import { isoWeekKey } from '../lib/week'
import IndicatorPicker from '../components/IndicatorPicker'
import EmptyState from '../components/EmptyState'

/**
 * Template-driven question drafting — no network call, no API key, works
 * offline. It produces editable starting points from the indicator text; the
 * teacher rewrites them into the final wording. Deliberately honest about what
 * it is: a scaffold, not an author.
 */
const TEMPLATES = {
  short: (indicator) => [
    `Explain what is meant by "${indicator}".`,
    `Give two examples of ${indicator.toLowerCase()} in everyday life.`,
    `Describe ${indicator.toLowerCase()} in your own words.`,
  ],
  essay: (indicator) => [
    `Discuss ${indicator.toLowerCase()}, giving three reasons and one example for each.`,
    `Write a short essay on why ${indicator.toLowerCase()} matters in your community.`,
  ],
  truefalse: (indicator) => [
    `True or false: ${indicator}.`,
  ],
  mcq: (indicator) => [
    `Which of the following best describes ${indicator.toLowerCase()}?`,
  ],
}

export default function QuestionGenerator() {
  const { user, profile } = useAuth()
  const toast = useToast()
  const [grade, setGrade] = useState('B1')
  const [subjectId, setSubjectId] = useState('')
  const [type, setType] = useState('short')
  const [marks, setMarks] = useState(3)
  const [indicatorIds, setIndicatorIds] = useState([])
  const [drafts, setDrafts] = useState([])
  const [saving, setSaving] = useState(false)
  const { subjects, loading: loadingSubjects, error: subjectsError } = useCurriculum(grade)
  const { lessons } = useSchedules(grade)

  const generate = () => {
    if (!indicatorIds.length) return toast.error('Choose at least one indicator.')
    const subjectName = subjects.find((s) => s.id === subjectId)?.name || subjectId
    const rows = indicatorIds.flatMap((indicator) => {
      const scheduled = lessons.find((lesson) => [lesson.indicatorCode, lesson.code].includes(indicator.code))
      const context = scheduled?.sessionTitle || scheduled?.performanceIndicator || indicator.description
      return (TEMPLATES[type] || TEMPLATES.short)(context).map((prompt) => ({
        type,
        grade,
        subjectId,
        subjectName,
        term: Number(scheduled?.term) || 1,
        week: Number(scheduled?.week) || null,
        prompt,
        answer: '',
        marks: Number(marks) || 3,
        options: [],
        indicatorIds: [indicator],
        indicatorCodes: [indicator.code],
      }))
    })
    setDrafts(rows)
    toast.success(`${rows.length} draft question(s) — edit before saving.`)
  }

  const updateDraft = (index, patch) => setDrafts((current) => current.map((draft, i) => (i === index ? { ...draft, ...patch } : draft)))

  const saveAll = async () => {
    const usable = drafts.filter((d) => d.prompt.trim())
    if (!usable.length) return toast.error('Nothing to save.')
    setSaving(true)
    try {
      await Promise.all(
        usable.map((draft) =>
          addDoc(collection(db, 'questions'), {
            ...draft,
            weekKey: isoWeekKey(),
            authorId: user.uid,
            authorName: profile?.name || 'Member',
            createdAt: serverTimestamp(),
          })
        )
      )
      toast.success(`${usable.length} question(s) added to the bank`)
      setDrafts([])
    } catch (error) {
      toast.error(`Could not save: ${error?.code || error.message}`)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div>
      <header className="mb-6 flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="page-title">Generate questions</h1>
          <p className="page-subtitle">Draft questions straight from an indicator, then edit and save the good ones.</p>
        </div>
        <Link to="/portal/questions" className="btn-secondary">Back to the bank</Link>
      </header>

      <div className="card space-y-5 p-6">
        <div className="grid gap-4 sm:grid-cols-4">
          <div>
            <label className="label-caps" htmlFor="g-grade">Grade</label>
            <select id="g-grade" className="input" value={grade} onChange={(e) => { setGrade(e.target.value); setSubjectId(''); setIndicatorIds([]) }}>
              {GRADES.map((g) => <option key={g} value={g}>{gradeLabel(g)}</option>)}
            </select>
          </div>
          <div>
            <label className="label-caps" htmlFor="g-subject">Subject</label>
            <SubjectSelect
              id="g-subject"
              className="input"
              grade={grade}
              subjects={subjects}
              loading={loadingSubjects}
              error={subjectsError}
              value={subjectId}
              onChange={(e) => { setSubjectId(e.target.value); setIndicatorIds([]) }}
            />
          </div>
          <div>
            <label className="label-caps" htmlFor="g-type">Question type</label>
            <select id="g-type" className="input" value={type} onChange={(e) => setType(e.target.value)}>
              <option value="short">Short answer</option>
              <option value="essay">Essay</option>
              <option value="mcq">Multiple choice</option>
              <option value="truefalse">True / false</option>
            </select>
          </div>
          <div>
            <label className="label-caps" htmlFor="g-marks">Marks each</label>
            <input id="g-marks" type="number" min="1" max="20" className="input" value={marks} onChange={(e) => setMarks(e.target.value)} />
          </div>
        </div>

        <div>
          <label className="label-caps">Indicators to draw from</label>
          <IndicatorPicker grade={grade} subjectId={subjectId} selected={indicatorIds} onChange={setIndicatorIds} />
        </div>

        <div className="flex justify-end">
          <button type="button" className="btn-primary" onClick={generate} disabled={!indicatorIds.length}>Generate drafts</button>
        </div>
      </div>

      <div className="mt-6 space-y-4">
        {drafts.length === 0 && (
          <EmptyState
            title="No drafts yet"
            message="Pick a grade, subject and one or more indicators. Beacon will draft a starting point for each — you decide what goes into the bank."
          />
        )}

        {drafts.map((draft, index) => (
          <div key={index} className="card p-5">
            <div className="flex items-center justify-between">
              <span className="chip">{draft.indicatorCodes.join(', ')}</span>
              <button type="button" className="btn-ghost px-2 py-1 text-xs" onClick={() => setDrafts((current) => current.filter((_, i) => i !== index))}>
                Discard
              </button>
            </div>
            <textarea
              rows={2}
              className="input mt-3"
              value={draft.prompt}
              onChange={(e) => updateDraft(index, { prompt: e.target.value })}
            />
            <input
              className="input mt-2"
              placeholder="Answer / marking notes"
              value={draft.answer}
              onChange={(e) => updateDraft(index, { answer: e.target.value })}
            />
          </div>
        ))}

        {drafts.length > 0 && (
          <div className="flex justify-end">
            <button type="button" className="btn-primary" onClick={saveAll} disabled={saving}>
              {saving ? 'Saving…' : `Save ${drafts.length} question(s) to the bank`}
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
