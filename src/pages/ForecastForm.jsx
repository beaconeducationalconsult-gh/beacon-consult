import { useEffect, useMemo, useState } from 'react'
import { useNavigate, useParams, useSearchParams } from 'react-router-dom'
import { addDoc, collection, doc, getDoc, serverTimestamp, updateDoc } from 'firebase/firestore'
import { db } from '../firebase'
import { useAuth } from '../context/AuthContext'
import { useToast } from '../context/ToastContext'
import { useCurriculum, useSchedules } from '../hooks/useCurriculum'
import SubjectSelect from '../components/SubjectSelect'
import { GRADES, TERMS, gradeLabel } from '../lib/grades'
import Stepper from '../components/Stepper'

const STEPS = ['Subject & term', 'Weekly rows', 'Review & save']

/** Build a scheme from the grade's curriculum schedule, then let the teacher edit. */
export default function ForecastForm() {
  const { forecastId } = useParams()
  const editing = Boolean(forecastId)
  const [params] = useSearchParams()
  const { user, profile } = useAuth()
  const toast = useToast()
  const navigate = useNavigate()

  const [step, setStep] = useState(0)
  const [grade, setGrade] = useState(params.get('grade') || 'B1')
  const [subjectId, setSubjectId] = useState(params.get('subject') || '')
  const [term, setTerm] = useState(Number(params.get('term')) || 1)
  const [visibility, setVisibility] = useState('members')
  const [rows, setRows] = useState([])
  const [notes, setNotes] = useState('')
  const [saving, setSaving] = useState(false)

  const { subjects, loading: loadingSubjects, error: subjectsError } = useCurriculum(grade)
  const { lessons, loading: loadingSchedule, error: scheduleError } = useSchedules(grade, subjectId)

  // Editing: load the stored scheme instead of the template.
  useEffect(() => {
    if (!editing) return
    getDoc(doc(db, 'weekly_forecasts', forecastId)).then((snap) => {
      if (!snap.exists()) return
      const data = snap.data()
      setGrade(data.grade)
      setSubjectId(data.subjectId)
      setTerm(data.term)
      setVisibility(data.visibility || 'members')
      setRows(data.rows || [])
      setNotes(data.notes || '')
      setStep(1)
    })
  }, [editing, forecastId])

  // Seed the weekly rows from the curriculum schedule for the chosen subject.
  const templateRows = useMemo(() => {
    if (!lessons?.length || !subjectId) return []
    const weekly = new Map()
    for (const lesson of lessons) {
      if (lesson.subjectId !== subjectId && lesson.subject !== subjectId) continue
      if (Number(lesson.term) !== Number(term)) continue
      const week = Number(lesson.week) || 1
      if (!weekly.has(week)) {
        weekly.set(week, {
          week,
          strandName: lesson.strandName || '',
          subStrandName: lesson.subStrandName || '',
          contentStandard: lesson.contentStandard || lesson.contentStandardDescription || '',
          indicatorCodes: [],
          resources: lesson.resources || '',
        })
      }
      const row = weekly.get(week)
      const code = lesson.indicatorCode || lesson.code
      if (code && !row.indicatorCodes.includes(code)) row.indicatorCodes.push(code)
      row.strandName ||= lesson.strandName || ''
      row.subStrandName ||= lesson.subStrandName || ''
      row.contentStandard ||= lesson.contentStandard || lesson.contentStandardDescription || ''
    }
    return [...weekly.values()].sort((a, b) => a.week - b.week)
  }, [lessons, subjectId, term])

  const useTemplate = () => {
    setRows(templateRows.map((row) => ({ ...row, indicators: row.indicatorCodes.join(', ') })))
    setStep(1)
  }

  const startBlank = () => {
    setRows(Array.from({ length: 12 }, (_, i) => ({ week: i + 1, strandName: '', subStrandName: '', contentStandard: '', indicatorCodes: [], indicators: '', resources: '' })))
    setStep(1)
  }

  const updateRow = (index, patch) => setRows((current) => current.map((row, i) => (i === index ? { ...row, ...patch } : row)))
  const addRow = () => setRows((current) => [...current, { week: current.length + 1, indicatorCodes: [], indicators: '', resources: '' }])
  const removeRow = (index) => setRows((current) => current.filter((_, i) => i !== index))

  const save = async () => {
    if (!subjectId) return toast.error('Choose a subject first.')
    setSaving(true)
    const subjectName = subjects.find((s) => s.id === subjectId)?.name || subjectId
    const payload = {
      subjectId,
      subjectName,
      grade,
      term: Number(term),
      visibility,
      notes,
      rows: rows.map((row) => ({
        ...row,
        week: Number(row.week) || 1,
        indicatorCodes: row.indicatorCodes?.length ? row.indicatorCodes : String(row.indicators || '').split(',').map((s) => s.trim()).filter(Boolean),
      })),
      updatedAt: serverTimestamp(),
    }
    try {
      if (editing) {
        await updateDoc(doc(db, 'weekly_forecasts', forecastId), payload)
        toast.success('Scheme updated')
        navigate(`/portal/forecasts/${forecastId}`)
      } else {
        const ref = await addDoc(collection(db, 'weekly_forecasts'), {
          ...payload,
          kind: 'scheme',
          authorId: user.uid,
          authorName: profile?.name || 'Member',
          createdAt: serverTimestamp(),
        })
        toast.success('Scheme saved')
        navigate(`/portal/forecasts/${ref.id}`)
      }
    } catch (error) {
      toast.error(`Could not save: ${error?.code || error.message}`)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div>
      <header className="mb-6">
        <h1 className="page-title">{editing ? 'Edit scheme' : 'New scheme of learning'}</h1>
        <p className="page-subtitle">Pick the class you teach; Beacon fills the weeks from the curriculum schedule.</p>
      </header>

      <Stepper steps={STEPS} current={step} onStep={setStep} />

      {step === 0 && (
        <div className="card space-y-4 p-6">
          <div className="grid gap-4 sm:grid-cols-3">
            <div>
              <label className="label-caps" htmlFor="grade">Grade</label>
              <select id="grade" className="input" value={grade} onChange={(e) => { setGrade(e.target.value); setSubjectId('') }}>
                {GRADES.map((g) => <option key={g} value={g}>{gradeLabel(g)}</option>)}
              </select>
            </div>
            <div>
              <label className="label-caps" htmlFor="subject">Subject</label>
              <SubjectSelect
                id="subject"
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
              <label className="label-caps" htmlFor="term">Term</label>
              <select id="term" className="input" value={term} onChange={(e) => setTerm(e.target.value)}>
                {TERMS.map((t) => <option key={t} value={t}>Term {t}</option>)}
              </select>
            </div>
          </div>

          <div>
            <label className="label-caps" htmlFor="visibility">Who can see it</label>
            <select id="visibility" className="input" value={visibility} onChange={(e) => setVisibility(e.target.value)}>
              <option value="members">Members of the network</option>
              <option value="public">Public</option>
              <option value="private">Only me (draft)</option>
            </select>
          </div>

          <div className="flex flex-wrap gap-3">
            <button type="button" className="btn-primary" onClick={useTemplate} disabled={!subjectId || loadingSchedule || templateRows.length === 0}>
              {loadingSchedule ? 'Loading schedule…' : `Use ${templateRows.length || ''} scheduled weeks`}
            </button>
            <button type="button" className="btn-secondary" onClick={startBlank}>Start blank</button>
          </div>
          {!loadingSchedule && subjectId && templateRows.length === 0 && (
            <p className="text-sm text-warning-700 dark:text-warning-500">
              {scheduleError
                ? 'The curriculum schedule for this grade could not be loaded — check your connection and reload, or start blank.'
                : 'No curriculum schedule exists for this subject and grade yet — start blank and fill it in yourself.'}
            </p>
          )}
        </div>
      )}

      {step === 1 && (
        <div className="space-y-4">
          {rows.map((row, index) => (
            <div key={index} className="card p-5">
              <div className="mb-3 flex items-center justify-between">
                <h2 className="card-title">Week {row.week}</h2>
                <button type="button" className="btn-ghost px-2 py-1 text-xs" onClick={() => removeRow(index)}>Remove</button>
              </div>
              <div className="grid gap-3 sm:grid-cols-2">
                <input className="input" placeholder="Strand" value={row.strandName || ''} onChange={(e) => updateRow(index, { strandName: e.target.value })} />
                <input className="input" placeholder="Sub-strand" value={row.subStrandName || ''} onChange={(e) => updateRow(index, { subStrandName: e.target.value })} />
              </div>
              <input className="input mt-3" placeholder="Content standard" value={row.contentStandard || ''} onChange={(e) => updateRow(index, { contentStandard: e.target.value })} />
              <input className="input mt-3 font-mono text-xs" placeholder="Indicator codes, comma separated" value={row.indicators ?? (row.indicatorCodes || []).join(', ')} onChange={(e) => updateRow(index, { indicators: e.target.value })} />
              <input className="input mt-3" placeholder="Teaching & learning materials" value={row.resources || ''} onChange={(e) => updateRow(index, { resources: e.target.value })} />
            </div>
          ))}
          <div className="flex flex-wrap gap-3">
            <button type="button" className="btn-secondary" onClick={addRow}>Add week</button>
            <button type="button" className="btn-primary" onClick={() => setStep(2)}>Review</button>
          </div>
        </div>
      )}

      {step === 2 && (
        <div className="space-y-4">
          <div className="card p-6">
            <p className="section-heading">Summary</p>
            <p className="mt-2 text-sm text-text">
              {subjects.find((s) => s.id === subjectId)?.name || subjectId} · {gradeLabel(grade)} · Term {term} · {rows.length} weeks
            </p>
            <div className="mt-4">
              <label className="label-caps" htmlFor="notes">Notes (printed under the table)</label>
              <textarea id="notes" rows={3} className="input" value={notes} onChange={(e) => setNotes(e.target.value)} />
            </div>
          </div>
          <div className="flex justify-end gap-3">
            <button type="button" className="btn-secondary" onClick={() => setStep(1)}>Back</button>
            <button type="button" className="btn-primary" onClick={save} disabled={saving}>
              {saving ? 'Saving…' : editing ? 'Save changes' : 'Save scheme'}
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
