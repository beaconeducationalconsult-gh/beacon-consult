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
import IndicatorPicker from '../components/IndicatorPicker'

const STEPS = ['Class & indicators', 'Lesson content', 'Review & save']

const empty = {
  subjectId: '',
  grade: 'B1',
  term: 1,
  week: 1,
  durationMinutes: 60,
  visibility: 'members',
  objectives: [],
  keywords: [],
  rpk: '',
  starter: [],
  main: [],
  plenary: [],
  assessment: '',
  competencies: [],
  resources: [],
  differentiation: '',
  indicatorIds: [],
}

/**
 * One textarea per list field — the simplest reliable UX on a phone.
 * Uncontrolled with a key derived from the committed value: the parent owns the
 * data, the field only pushes changes on blur, and no effect has to sync state.
 */
function ListField({ label, hint, value, onChange, rows = 4 }) {
  const initial = (value || []).join('\n')
  return (
    <div>
      <label className="label-caps">{label}</label>
      {hint && <p className="mb-1 text-xs text-slate-500">{hint}</p>}
      <textarea
        key={initial}
        rows={rows}
        className="input"
        defaultValue={initial}
        onBlur={(event) => onChange(event.target.value.split('\n').map((line) => line.trim()).filter(Boolean))}
      />
    </div>
  )
}

function ChipsField({ label, hint, value, onChange }) {
  const initial = (value || []).join(', ')
  return (
    <div>
      <label className="label-caps">{label}</label>
      {hint && <p className="mb-1 text-xs text-slate-500">{hint}</p>}
      <input
        key={initial}
        className="input"
        defaultValue={initial}
        onBlur={(event) => onChange(event.target.value.split(',').map((item) => item.trim()).filter(Boolean))}
      />
    </div>
  )
}

export default function LessonPlanForm() {
  const { planId } = useParams()
  const editing = Boolean(planId)
  const [params] = useSearchParams()
  const { user, profile } = useAuth()
  const toast = useToast()
  const navigate = useNavigate()

  const [form, setForm] = useState({ ...empty, grade: params.get('grade') || 'B1' })
  const [step, setStep] = useState(0)
  const [loading, setLoading] = useState(editing)
  const [saving, setSaving] = useState(false)
  const [prefilling, setPrefilling] = useState(false)

  const { subjects, indicators, loading: loadingSubjects, error: subjectsError } = useCurriculum(form.grade)
  const { lessons } = useSchedules(form.grade, form.subjectId)

  // Deep link from the curriculum browser: ?indicator=B1.1.1.1.1&grade=B5
  // Resolved during render (React's documented "adjust state when a prop
  // changes" pattern) once the grade's indicators have loaded.
  const [urlHydrated, setUrlHydrated] = useState(false)
  if (!editing && !urlHydrated && indicators.length > 0) {
    const code = params.get('indicator')
    const match = code ? indicators.find((i) => i.code === code) : null
    setUrlHydrated(true)
    if (match) {
      setForm((current) => ({
        ...current,
        subjectId: match.subjectId || current.subjectId,
        indicatorIds: [{
          indicatorId: match.id || match.code,
          code: match.code,
          description: match.description,
          strandName: match.strandName,
          subStrandName: match.subStrandName,
          contentStandard: match.contentStandardDescription || match.contentStandardCode,
        }],
      }))
    }
  }

  useEffect(() => {
    if (!editing) return
    getDoc(doc(db, 'lesson_plans', planId))
      .then((snap) => {
        if (snap.exists()) setForm({ ...empty, ...snap.data() })
      })
      .finally(() => setLoading(false))
  }, [editing, planId])

  /** Pull the curriculum row for the first chosen indicator into the plan. */
  const prefillFromCurriculum = () => {
    const first = form.indicatorIds[0]
    if (!first) return toast.error('Choose an indicator first.')
    setPrefilling(true)
    const scheduled = lessons.find((lesson) => [lesson.indicatorCode, lesson.code].includes(first.code))
    setForm((current) => ({
      ...current,
      strandName: first.strandName || scheduled?.strandName || '',
      subStrandName: first.subStrandName || scheduled?.subStrandName || '',
      contentStandard: first.contentStandard || scheduled?.contentStandard || '',
      indicatorDescription: first.description || '',
      performanceIndicator: scheduled?.performanceIndicator || '',
      week: scheduled?.week ? Number(scheduled.week) : current.week,
      term: scheduled?.term ? Number(scheduled.term) : current.term,
      objectives: current.objectives.length ? current.objectives : [first.description ? `By the end of the lesson, learners will be able to ${lowerFirst(first.description)}` : ''],
      keywords: current.keywords.length ? current.keywords : (scheduled?.keywords ? [].concat(scheduled.keywords) : []),
      resources: current.resources.length ? current.resources : (scheduled?.resources ? [].concat(scheduled.resources) : []),
      starter: current.starter.length ? current.starter : [].concat(scheduled?.starter || []),
      main: current.main.length ? current.main : [].concat(scheduled?.main || []),
      plenary: current.plenary.length ? current.plenary : [].concat(scheduled?.plenary || []),
      rpk: current.rpk || scheduled?.rpk || '',
      assessment: current.assessment || scheduled?.assessment || '',
    }))
    setPrefilling(false)
    toast.success('Filled from the curriculum — edit anything you like.')
  }

  const subjectName = useMemo(
    () => subjects.find((s) => s.id === form.subjectId)?.name || form.subjectId,
    [subjects, form.subjectId]
  )

  const save = async () => {
    if (!form.subjectId) return toast.error('Choose a subject.')
    if (form.indicatorIds.length === 0) return toast.error('Choose at least one indicator.')
    setSaving(true)
    const payload = {
      ...form,
      subjectName,
      term: Number(form.term) || 1,
      week: Number(form.week) || 1,
      durationMinutes: Number(form.durationMinutes) || 60,
      indicatorCodes: form.indicatorIds.map((i) => i.code),
      updatedAt: serverTimestamp(),
    }
    try {
      if (editing) {
        await updateDoc(doc(db, 'lesson_plans', planId), payload)
        toast.success('Lesson plan updated')
        navigate(`/portal/plans/${planId}`)
      } else {
        const ref = await addDoc(collection(db, 'lesson_plans'), {
          ...payload,
          authorId: user.uid,
          authorName: profile?.name || 'Member',
          createdAt: serverTimestamp(),
        })
        toast.success('Lesson plan saved')
        navigate(`/portal/plans/${ref.id}`)
      }
    } catch (error) {
      toast.error(`Could not save: ${error?.code || error.message}`)
    } finally {
      setSaving(false)
    }
  }

  if (loading) return <div className="card h-96 animate-pulse" />

  return (
    <div>
      <header className="mb-6">
        <h1 className="page-title">{editing ? 'Edit lesson plan' : 'New lesson plan'}</h1>
        <p className="page-subtitle">Plans follow the printed format: objectives, starter, main activities, plenary and assessment.</p>
      </header>

      <Stepper steps={STEPS} current={step} onStep={setStep} />

      {step === 0 && (
        <div className="card space-y-5 p-6">
          <div className="grid gap-4 sm:grid-cols-4">
            <div>
              <label className="label-caps" htmlFor="grade">Grade</label>
              <select id="grade" className="input" value={form.grade} onChange={(e) => setForm({ ...form, grade: e.target.value, subjectId: '', indicatorIds: [] })}>
                {GRADES.map((g) => <option key={g} value={g}>{gradeLabel(g)}</option>)}
              </select>
            </div>
            <div>
              <label className="label-caps" htmlFor="subject">Subject</label>
              <SubjectSelect
                id="subject"
                className="input"
                grade={form.grade}
                subjects={subjects}
                loading={loadingSubjects}
                error={subjectsError}
                value={form.subjectId}
                onChange={(e) => setForm({ ...form, subjectId: e.target.value, indicatorIds: [] })}
              />
            </div>
            <div>
              <label className="label-caps" htmlFor="term">Term</label>
              <select id="term" className="input" value={form.term} onChange={(e) => setForm({ ...form, term: e.target.value })}>
                {TERMS.map((t) => <option key={t} value={t}>Term {t}</option>)}
              </select>
            </div>
            <div>
              <label className="label-caps" htmlFor="week">Week</label>
              <input id="week" type="number" min="1" max="14" className="input" value={form.week} onChange={(e) => setForm({ ...form, week: e.target.value })} />
            </div>
          </div>

          <div>
            <label className="label-caps">Indicators</label>
            <IndicatorPicker
              grade={form.grade}
              subjectId={form.subjectId}
              selected={form.indicatorIds}
              onChange={(indicatorIds) => setForm({ ...form, indicatorIds })}
            />
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <button type="button" className="btn-secondary" onClick={prefillFromCurriculum} disabled={prefilling || form.indicatorIds.length === 0}>
              {prefilling ? 'Filling…' : 'Fill from curriculum'}
            </button>
            <p className="card-meta">Uses the indicator, plus the scheduled lesson content if the grade has a schedule.</p>
          </div>

          <div className="flex justify-end">
            <button type="button" className="btn-primary" onClick={() => setStep(1)} disabled={form.indicatorIds.length === 0}>
              Continue
            </button>
          </div>
        </div>
      )}

      {step === 1 && (
        <div className="card space-y-5 p-6">
          <div className="grid gap-4 sm:grid-cols-2">
            <ListField label="Learning objectives" hint="One per line" value={form.objectives} onChange={(objectives) => setForm({ ...form, objectives })} rows={3} />
            <ChipsField label="Key words" hint="Comma separated" value={form.keywords} onChange={(keywords) => setForm({ ...form, keywords })} />
          </div>

          <div>
            <label className="label-caps" htmlFor="rpk">Relevant previous knowledge</label>
            <textarea id="rpk" rows={2} className="input" value={form.rpk || ''} onChange={(e) => setForm({ ...form, rpk: e.target.value })} />
          </div>

          <ListField label="Starter / introduction" hint="One activity per line" value={form.starter} onChange={(starter) => setForm({ ...form, starter })} />
          <ListField label="Main activities" hint="One activity per line, in teaching order" value={form.main} onChange={(main) => setForm({ ...form, main })} rows={6} />
          <ListField label="Plenary / conclusion" hint="One activity per line" value={form.plenary} onChange={(plenary) => setForm({ ...form, plenary })} />

          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <label className="label-caps" htmlFor="assessment">Assessment</label>
              <textarea id="assessment" rows={3} className="input" value={form.assessment || ''} onChange={(e) => setForm({ ...form, assessment: e.target.value })} />
            </div>
            <div>
              <label className="label-caps" htmlFor="differentiation">Differentiation / support</label>
              <textarea id="differentiation" rows={3} className="input" value={form.differentiation || ''} onChange={(e) => setForm({ ...form, differentiation: e.target.value })} />
            </div>
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <ChipsField label="Core competencies" hint="Comma separated" value={form.competencies} onChange={(competencies) => setForm({ ...form, competencies })} />
            <ChipsField label="Teaching & learning materials" hint="Comma separated" value={form.resources} onChange={(resources) => setForm({ ...form, resources })} />
          </div>

          <div className="flex justify-between">
            <button type="button" className="btn-secondary" onClick={() => setStep(0)}>Back</button>
            <button type="button" className="btn-primary" onClick={() => setStep(2)}>Review</button>
          </div>
        </div>
      )}

      {step === 2 && (
        <div className="card space-y-4 p-6">
          <div>
            <p className="section-heading">Class</p>
            <p className="mt-1 text-sm text-slate-700">
              {subjectName} · {gradeLabel(form.grade)} · Term {form.term}, week {form.week} · {form.durationMinutes} minutes
            </p>
          </div>
          <div>
            <p className="section-heading">Indicators</p>
            <ul className="mt-1 space-y-1">
              {form.indicatorIds.map((item) => (
                <li key={item.indicatorId} className="text-sm text-slate-700">
                  <span className="font-mono text-xs text-brand-700">{item.code}</span> — {item.description}
                </li>
              ))}
            </ul>
          </div>
          <dl className="grid grid-cols-2 gap-3 text-sm sm:grid-cols-4">
            {[['Objectives', form.objectives.length], ['Starter steps', form.starter.length], ['Main steps', form.main.length], ['Plenary steps', form.plenary.length]].map(([label, count]) => (
              <div key={label} className="rounded-lg bg-slate-50 p-3">
                <dt className="card-meta">{label}</dt>
                <dd className="font-semibold text-slate-800">{count}</dd>
              </div>
            ))}
          </dl>
          <div>
            <label className="label-caps" htmlFor="duration">Duration (minutes)</label>
            <input id="duration" type="number" min="30" max="180" step="5" className="input max-w-40" value={form.durationMinutes} onChange={(e) => setForm({ ...form, durationMinutes: e.target.value })} />
          </div>
          <div>
            <label className="label-caps" htmlFor="plan-visibility">Who can see it</label>
            <select id="plan-visibility" className="input" value={form.visibility} onChange={(e) => setForm({ ...form, visibility: e.target.value })}>
              <option value="members">Members of the network</option>
              <option value="public">Public</option>
            </select>
          </div>
          <div className="flex justify-between">
            <button type="button" className="btn-secondary" onClick={() => setStep(1)}>Back</button>
            <button type="button" className="btn-primary" onClick={save} disabled={saving}>
              {saving ? 'Saving…' : editing ? 'Save changes' : 'Save lesson plan'}
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

const lowerFirst = (text) => {
  const value = String(text || '')
  return value.charAt(0).toLowerCase() + value.slice(1)
}
